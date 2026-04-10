"""Research Agent — autonomously discovers brand data sources and extracts brand seeds."""

import json
import os
import time
from typing import Optional

from .llm import chat_json, chat
from .web_searcher import _search_metaso, _search_tavily
from .crawler import _convert_page


class ResearchAgent:
    """Autonomous research agent that discovers brand data sources and extracts brand seeds.

    Works like a researcher:
    1. Receive a task (e.g., "expand automotive brand library")
    2. Search the web for brand directories/rankings
    3. Extract brand names + official URLs from those pages
    4. Evaluate data source quality, record learnings
    5. Return high-quality brand seed list
    """

    def __init__(self, knowledge_file: str = "data/research_knowledge.json"):
        self.knowledge_file = knowledge_file
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> dict:
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sources": {}, "industries": {}}

    def _save_knowledge(self):
        os.makedirs(os.path.dirname(self.knowledge_file), exist_ok=True)
        with open(self.knowledge_file, "w", encoding="utf-8") as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)

    def discover_brands(self, industry: str, limit: int = 20) -> list[dict]:
        """Discover brand seeds for a given industry.

        Steps:
        1. Check if we have known data sources for this industry
        2. If yes, crawl directly from those sources
        3. If no, use search engine to discover new data sources
        4. Extract brand names + URLs from pages
        5. Use LLM to verify extraction reasonableness
        6. Update knowledge base

        Returns: [{"name": "BrandName", "url": "https://official.site", "source": "source_url", "confidence": 0.9}, ...]
        """
        print(f"🔬 ResearchAgent: discovering brands for '{industry}'")

        known_sources = self._get_known_sources(industry)
        if known_sources:
            print(f"   📚 Using {len(known_sources)} known data sources")
            all_brands = []
            for source in known_sources:
                brands = self._extract_brands_from_page(
                    source["url"], page_content=None, industry=industry
                )
                all_brands.extend(brands)
            all_brands = self._dedupe_brands(all_brands)
            all_brands = self._verify_urls(all_brands)
            if len(all_brands) >= limit:
                return all_brands[:limit]

        new_sources = self._search_for_sources(industry)
        print(f"   🔍 Found {len(new_sources)} new data sources")

        all_brands = list(
            self.knowledge.get("industries", {}).get(industry, {}).get("brands", [])
        )

        for source in new_sources:
            brands = self._extract_brands_from_page(
                source["url"], page_content=None, industry=industry
            )
            all_brands.extend(brands)

            quality_score = self._assess_source_quality(source["url"], brands)
            self._update_knowledge(industry, source["url"], len(brands), quality_score)

            if len(all_brands) >= limit * 2:
                break

        all_brands = self._dedupe_brands(all_brands)
        all_brands = self._verify_urls(all_brands)

        if len(all_brands) > limit:
            all_brands = all_brands[:limit]

        print(f"   ✅ Returning {len(all_brands)} brand seeds")
        return all_brands

    def _get_known_sources(self, industry: str) -> list[dict]:
        industries_data = self.knowledge.get("industries", {})
        if industry in industries_data:
            sources = industries_data[industry].get("sources", [])
            return [s for s in sources if s.get("quality_score", 0) >= 3]
        return []

    def _search_for_sources(self, industry: str) -> list[dict]:
        """Search for brand directory/ranking pages.

        Search strategy:
        - Chinese: "{industry}品牌大全", "{industry}十大品牌", "{industry}品牌排行榜"
        - English: "{industry} brand directory", "{industry} top brands ranking"

        Returns: [{"url": "source_url", "title": "Page Title", "type": "ranking/directory/article"}]
        """
        sources = []

        chinese_queries = [
            f"{industry}品牌大全",
            f"{industry}十大品牌",
            f"{industry}品牌排行榜",
        ]
        english_queries = [
            f"{industry} top brands ranking",
            f"{industry} brand directory",
        ]

        all_queries = chinese_queries + english_queries
        seen_urls = set()

        for query in all_queries:
            if len(sources) >= 5:
                break

            if any(cn_word in query for cn_word in ["品牌", "排行", "大全"]):
                result = _search_metaso(query, size=5)
            else:
                result = _search_tavily(query, max_results=5)

            for r in result.get("results", []):
                url = r.get("url", "")
                title = r.get("title", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    page_type = self._classify_source_type(title, r.get("content", ""))
                    sources.append(
                        {
                            "url": url,
                            "title": title,
                            "type": page_type,
                        }
                    )

        return sources[:5]

    def _classify_source_type(self, title: str, content: str) -> str:
        title_lower = title.lower()
        content_lower = content.lower()
        if any(
            kw in title_lower or kw in content_lower
            for kw in ["排行", "排名", "top", "ranking", "best"]
        ):
            return "ranking"
        if any(
            kw in title_lower or kw in content_lower
            for kw in ["大全", "目录", "directory", "list"]
        ):
            return "directory"
        return "article"

    def _extract_brands_from_page(
        self, page_url: str, page_content: Optional[str], industry: str
    ) -> list[dict]:
        """Extract brand names and official URLs from page content using LLM.

        Key: LLM only extracts, does NOT fabricate. If page content doesn't have an official URL,
        mark it as empty — will be supplemented via search later.
        """
        if not page_content:
            page = _convert_page(page_url)
            if page and page.get("content"):
                page_content = page["content"][:15000]
            else:
                page_content = ""

        if not page_content or len(page_content) < 200:
            print(f"   ⚠️ Could not fetch content from {page_url}")
            return []

        prompt = f"""你是一个品牌研究助手。你的任务是从以下网页内容中提取品牌信息。

## 行业: {industry}

## 重要规则：
1. 只提取网页中**明确提到**的品牌名称和官方网站URL
2. 不要编造、猜测或推断任何信息
3. 如果网页中没有提供某品牌的官网URL，该字段留空
4. 只提取在网页中明确列出的品牌，不要提取网页提到但未正式列出的品牌
5. 优先提取具有官网URL的品牌

## 网页内容:
{page_content[:12000]}

## 输出格式（严格JSON数组）：
[
  {{"name": "品牌名称", "url": "官方网站URL（如有）", "source": "{page_url}"}},
  ...
]

只输出JSON数组，不要包含任何其他文字。如果网页中没有品牌信息，返回空数组 []。"""

        try:
            result = chat_json(
                prompt,
                system="你是一个严格的事实提取助手。只从给定内容中提取信息，不要编造。输出严格JSON。",
                max_tokens=4000,
            )

            if isinstance(result, list):
                brands = []
                for item in result:
                    if isinstance(item, dict) and item.get("name"):
                        name = item.get("name", "").strip()
                        url = item.get("url", "").strip()
                        if name:
                            brands.append(
                                {
                                    "name": name,
                                    "url": url
                                    if url and url.startswith("http")
                                    else "",
                                    "source": page_url,
                                    "confidence": 0.8 if url else 0.4,
                                }
                            )
                return brands

            if isinstance(result, dict) and "brands" in result:
                brands = []
                for item in result.get("brands", []):
                    if isinstance(item, dict) and item.get("name"):
                        name = item.get("name", "").strip()
                        url = item.get("url", "").strip()
                        if name:
                            brands.append(
                                {
                                    "name": name,
                                    "url": url
                                    if url and url.startswith("http")
                                    else "",
                                    "source": page_url,
                                    "confidence": 0.8 if url else 0.4,
                                }
                            )
                return brands

        except Exception as e:
            print(f"   ⚠️ LLM extraction failed for {page_url}: {e}")

        return []

    def _verify_urls(self, brands: list[dict]) -> list[dict]:
        """Verify extracted URLs are accessible. For brands without URLs, try to search for official site."""
        verified = []
        for brand in brands:
            url = brand.get("url", "")
            name = brand.get("name", "")

            if url and url.startswith("http"):
                verified.append(brand)
            elif name:
                search_query = f"{name} 官网 官方网站"
                result = _search_metaso(search_query, size=3)
                found_url = ""
                for r in result.get("results", []):
                    content = r.get("content", "").lower()
                    title = r.get("title", "").lower()
                    if (
                        "官网" in r.get("title", "")
                        or "官网" in r.get("content", "")[:200]
                    ):
                        found_url = r.get("url", "")
                        break
                    if name.lower() in title and (
                        "官网" in content[:200] or "official" in content[:200]
                    ):
                        found_url = r.get("url", "")
                        break

                if found_url:
                    brand["url"] = found_url
                    brand["confidence"] = 0.7
                    verified.append(brand)
                else:
                    brand["url"] = ""
                    brand["confidence"] = 0.3
                    verified.append(brand)
            else:
                verified.append(brand)

        return verified

    def _dedupe_brands(self, brands: list[dict]) -> list[dict]:
        seen = {}
        for brand in brands:
            name = brand.get("name", "").strip()
            if name:
                key = name.lower()
                if key not in seen:
                    seen[key] = brand
                else:
                    existing = seen[key]
                    if not existing.get("url") and brand.get("url"):
                        existing["url"] = brand["url"]
                        existing["confidence"] = brand.get("confidence", 0.5)
        return list(seen.values())

    def _assess_source_quality(self, source_url: str, brands: list[dict]) -> float:
        if not brands:
            return 0.0
        urls_with_url = sum(1 for b in brands if b.get("url"))
        url_ratio = urls_with_url / len(brands)
        count_score = min(len(brands) / 20, 1.0)
        quality_score = (url_ratio * 0.6) + (count_score * 0.4)
        return round(quality_score * 10, 1)

    def _update_knowledge(
        self, industry: str, source_url: str, brands_found: int, quality_score: float
    ):
        if "industries" not in self.knowledge:
            self.knowledge["industries"] = {}
        if industry not in self.knowledge["industries"]:
            self.knowledge["industries"][industry] = {"sources": [], "brands": []}

        industry_data = self.knowledge["industries"][industry]
        sources = industry_data.get("sources", [])

        existing_idx = None
        for i, s in enumerate(sources):
            if s.get("url") == source_url:
                existing_idx = i
                break

        source_entry = {
            "url": source_url,
            "brands_found": brands_found,
            "quality_score": quality_score,
        }

        if existing_idx is not None:
            sources[existing_idx] = source_entry
        else:
            sources.append(source_entry)

        industry_data["sources"] = sources
        self._save_knowledge()
