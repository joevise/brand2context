"""Step 3: Web search expansion — Tavily (global) + Metaso (China)."""

import re
import requests
from .config import (
    TAVILY_API_KEY,
    TAVILY_ENDPOINT,
    METASO_API_KEY,
    METASO_SEARCH_ENDPOINT,
    METASO_READER_ENDPOINT,
)


def _is_china_brand(url: str, brand_name: str) -> bool:
    """Determine if a brand is China-focused based on URL and name."""
    # Domain-based detection
    china_tlds = [".cn", ".com.cn", ".net.cn", ".org.cn"]
    if any(url.lower().endswith(tld) or f"{tld}/" in url.lower() for tld in china_tlds):
        return True

    # Chinese character detection
    if brand_name and re.search(r"[\u4e00-\u9fff]", brand_name):
        return True

    # Known China domains
    china_domains = [
        "qq.com",
        "baidu.com",
        "taobao.com",
        "jd.com",
        "meituan.com",
        "bytedance.com",
        "163.com",
        "bilibili.com",
        "xiaohongshu.com",
        "pinduoduo.com",
        "douyin.com",
        "weibo.com",
    ]
    for d in china_domains:
        if d in url.lower():
            return True

    return False


def _search_metaso(query: str, size: int = 5, include_summary: bool = True) -> dict:
    """Search using Metaso (密塔搜索) API."""
    if not METASO_API_KEY:
        return {"query": query, "answer": "", "results": []}

    try:
        resp = requests.post(
            METASO_SEARCH_ENDPOINT,
            headers={
                "Authorization": f"Bearer {METASO_API_KEY}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "q": query,
                "scope": "webpage",
                "includeSummary": include_summary,
                "size": str(size),
                "includeRawContent": False,
                "conciseSnippet": False,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"   ⚠️ Metaso search returned {resp.status_code}")
            return {"query": query, "answer": "", "results": []}

        data = resp.json()
        webpages = data.get("webpages", [])

        results = []
        for wp in webpages:
            content = wp.get("snippet", "") or wp.get("summary", "")
            results.append(
                {
                    "title": wp.get("title", ""),
                    "url": wp.get("link", ""),
                    "content": content[:800],
                }
            )

        return {
            "query": query,
            "answer": "",  # Metaso doesn't have a direct answer field
            "results": results,
            "source": "metaso",
        }
    except Exception as e:
        print(f"   ⚠️ Metaso search '{query}' failed: {e}")
        return {"query": query, "answer": "", "results": []}


def _search_tavily(query: str, max_results: int = 5) -> dict:
    """Search using Tavily API."""
    if not TAVILY_API_KEY:
        return {"query": query, "answer": "", "results": []}

    try:
        resp = requests.post(
            TAVILY_ENDPOINT,
            json={"query": query, "max_results": max_results, "include_answer": True},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TAVILY_API_KEY}",
            },
            timeout=30,
        )
        if resp.status_code == 401:
            print(f"   ❌ Tavily auth failed")
            return {"query": query, "answer": "", "results": []}
        resp.raise_for_status()
        data = resp.json()

        return {
            "query": query,
            "answer": data.get("answer", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                }
                for r in data.get("results", [])
            ],
            "source": "tavily",
        }
    except Exception as e:
        print(f"   ⚠️ Tavily search '{query}' failed: {e}")
        return {"query": query, "answer": "", "results": []}


def _generate_smart_queries(
    clues: dict, pages: list[dict] = None, existing_results: list[dict] = None
) -> list[str]:
    """Generate supplementary search queries based on missing information in clues.

    Args:
        clues: Brand clues dict with extracted information
        pages: List of crawled page dicts (optional)
        existing_results: List of existing search results to avoid duplicate queries (optional)

    Returns:
        List of up to 5 supplementary query strings
    """
    brand_name = clues.get("brand_name", "")
    category = clues.get("category", "").lower()
    queries = []

    if not brand_name:
        return queries

    founded = clues.get("founded")
    headquarters = clues.get("headquarters")
    if not founded or not headquarters:
        queries.append(f"{brand_name} 创始人 成立时间 总部")

    products = clues.get("products", [])
    if not products or len(products) < 3:
        queries.append(f"{brand_name} 产品线 全部产品")

    if "科技" in category or "ai" in category or "人工智能" in category:
        queries.append(f"{brand_name} 技术架构 融资")

    if "消费" in category or "食品" in category or "饮料" in category:
        queries.append(f"{brand_name} 销量 市场份额")

    if "汽车" in category or "车辆" in category:
        queries.append(f"{brand_name} 销量排名 车型")

    queries.append(f"{brand_name} 竞品对比 vs")
    queries.append(f"{brand_name} 用户评价 口碑")

    return queries[:5]


def _dedupe_results(results: list[dict]) -> list[dict]:
    """Deduplicate search results by URL and content similarity.

    Args:
        results: List of search result dicts with 'url' and 'content' fields

    Returns:
        Deduplicated list of results
    """
    seen_urls = set()
    seen_content_prefixes = set()
    deduped = []

    for r in results:
        url = r.get("url", "")
        content = r.get("content", "")
        content_prefix = content[:100] if content else ""

        if url and url not in seen_urls:
            seen_urls.add(url)

            if content_prefix and content_prefix in seen_content_prefixes:
                continue
            seen_content_prefixes.add(content_prefix)

            deduped.append(r)
        elif not url and content_prefix and content_prefix not in seen_content_prefixes:
            seen_content_prefixes.add(content_prefix)
            deduped.append(r)

    return deduped


def search_expand(clues: dict, pages: list[dict] = None) -> list[dict]:
    """Run web searches based on extracted clues.

    Uses dual-engine strategy:
    - China brands: Metaso (primary) + Tavily (supplementary global context)
    - Global brands: Tavily (primary) + Metaso (supplementary China market context)
    """
    brand = clues.get("brand_name", "")
    company = clues.get("legal_name", "")
    category = clues.get("category", "")
    url = clues.get("url", "")

    if not brand and not company:
        print("⏭️  Skipping web search (no brand name extracted)")
        return []

    name = brand or company
    is_china = _is_china_brand(url, name)

    if is_china:
        print(f"🔎 中国品牌模式: {name} — 密塔搜索(主) + Tavily(辅)")
    else:
        print(f"🔎 国际品牌模式: {name} — Tavily(主) + 密塔搜索(辅)")

    results = []

    if is_china:
        # ===== CHINA BRAND: Metaso primary =====
        metaso_queries = [
            f"{name} 品牌介绍",
            f"{name} 产品 服务",
            f"{name} 用户评价 口碑",
            f"{name} 最新动态 新闻 2026",
        ]
        if company and company != brand:
            metaso_queries.append(f"{company} 公司 融资")
        if category:
            metaso_queries.append(f"{name} {category} 行业地位")

        for q in metaso_queries:
            r = _search_metaso(q, size=5)
            if r["results"]:
                results.append(r)
                print(f"   ✅ [密塔] '{q}' → {len(r['results'])} results")
            else:
                print(f"   ⚠️ [密塔] '{q}' → 0 results")

        # Supplementary Tavily for global perspective
        tavily_queries = [
            f"{name} brand",
            f"{name} products services",
        ]
        for q in tavily_queries:
            r = _search_tavily(q, max_results=3)
            if r["results"]:
                results.append(r)
                print(f"   ✅ [Tavily] '{q}' → {len(r['results'])} results")

    else:
        # ===== GLOBAL BRAND: Tavily primary =====
        tavily_queries = [
            f"{name}",
            f"{name} review",
        ]
        if company and company != brand:
            tavily_queries.append(f"{company} funding investors")
        if category:
            tavily_queries.append(f"{name} {category}")
        tavily_queries.append(f"{name} latest news 2026")

        for q in tavily_queries:
            r = _search_tavily(q, max_results=5)
            if r["results"]:
                results.append(r)
                print(f"   ✅ [Tavily] '{q}' → {len(r['results'])} results")
            else:
                print(f"   ⚠️ [Tavily] '{q}' → 0 results")

        # Supplementary Metaso for China market context
        metaso_queries = [
            f"{name} 中国市场",
            f"{name} 品牌评价",
        ]
        for q in metaso_queries:
            r = _search_metaso(q, size=3)
            if r["results"]:
                results.append(r)
                print(f"   ✅ [密塔] '{q}' → {len(r['results'])} results")

    all_results_flat = []
    for r in results:
        all_results_flat.extend(r.get("results", []))

    before_dedupe = len(all_results_flat)

    smart_queries = _generate_smart_queries(clues, pages, results)
    if smart_queries:
        print(f"   🔍 生成 {len(smart_queries)} 个补充 query: {smart_queries}")
        for q in smart_queries:
            if is_china:
                sr = _search_metaso(q, size=5)
                src = "密塔"
            else:
                sr = _search_tavily(q, max_results=5)
                src = "Tavily"

            if sr["results"]:
                results.append(sr)
                print(f"   ✅ [{src}] '{q}' → {len(sr['results'])} results")
            else:
                print(f"   ⚠️ [{src}] '{q}' → 0 results")

    all_results_flat = []
    for r in results:
        all_results_flat.extend(r.get("results", []))

    deduped_flat = _dedupe_results(all_results_flat)
    after_dedupe = len(deduped_flat)

    print(
        f"   🧹 去重结果: {before_dedupe} → {after_dedupe} (去重 {before_dedupe - after_dedupe} 条)"
    )

    return results


def metaso_read_url(url: str) -> str:
    """Use Metaso Reader API to extract content from a URL.

    This is a fallback when link2context crawling fails.
    Returns the extracted text content.
    """
    if not METASO_API_KEY:
        return ""

    try:
        resp = requests.post(
            METASO_READER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {METASO_API_KEY}",
                "Accept": "text/plain",
                "Content-Type": "application/json",
            },
            json={"url": url},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.text[:20000]  # Limit content size
        else:
            print(f"   ⚠️ Metaso reader returned {resp.status_code}")
            return ""
    except Exception as e:
        print(f"   ⚠️ Metaso reader failed: {e}")
        return ""
