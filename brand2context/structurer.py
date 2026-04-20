"""Step 4: LLM structured extraction — the core of Brand2Context."""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from .llm import chat_json
from .config import SCHEMA_PATH

DIMENSION_CONTEXT_KEYWORDS = {
    "identity": [
        "about",
        "story",
        "mission",
        "vision",
        "values",
        "founder",
        "team",
        "history",
        "career",
    ],
    "offerings": ["product", "service", "pricing", "solution", "feature", "offering"],
    "differentiation": [
        "about",
        "product",
        "competitive",
        "advantage",
        "unique",
        "technology",
        "patent",
    ],
    "trust": [
        "partner",
        "investor",
        "press",
        "certification",
        "award",
        "media",
        "testimonial",
    ],
    "experience": ["faq", "support", "help", "warranty", "service", "customer"],
    "access": ["contact", "store", "download", "location", "address", "phone", "email"],
    "content": ["blog", "news", "press", "announcement", "article"],
    "perception": ["review", "social", "media", "brand", "perception", "personality"],
    "decision_factors": [
        "pricing",
        "review",
        "product",
        "compare",
        "factor",
        "decision",
    ],
    "vitality": ["news", "blog", "update", "launch", "campaign", "event", "growth"],
    "campaigns": [
        "campaign",
        "event",
        "promotion",
        "collaboration",
        "launch",
        "news",
        "blog",
    ],
}


def _select_context_for_dimension(
    dimension: str,
    pages: list[dict],
    search_results: list[dict],
    social_results: list[dict],
    clues: dict,
) -> str:
    """Select and filter context relevant to a specific dimension."""
    keywords = DIMENSION_CONTEXT_KEYWORDS.get(dimension, [])
    context_parts = []

    if keywords:
        for page in pages:
            url_lower = page.get("url", "").lower()
            if any(kw in url_lower for kw in keywords):
                context_parts.append(
                    f"--- {page.get('url', '')} ---\n{page['content']}\n"
                )

    if not context_parts and pages:
        context_parts.append(
            f"--- {pages[0].get('url', '')} ---\n{pages[0]['content']}\n"
        )

    search_keywords_map = {
        "differentiation": ["competitive", "compare", "alternative"],
        "trust": ["review", "testimonial", "partner", "investor"],
        "perception": ["brand", "review", "social media", "opinion"],
        "decision_factors": ["pricing", "review", "vs", "compare"],
        "vitality": ["news", "latest", "update", "announcement"],
        "campaigns": ["campaign", "event", "promotion", "launch"],
    }
    sr_keywords = search_keywords_map.get(dimension, [])
    for sr in search_results:
        query_lower = sr.get("query", "").lower()
        source = sr.get("source", "")
        # Social media search results are valuable for many dimensions — don't filter
        is_social = "social" in source
        if is_social or not sr_keywords or any(kw in query_lower for kw in sr_keywords):
            sr_text = f"\n--- Search: {sr['query']} ---\n"
            if sr.get("answer"):
                sr_text += f"Answer: {sr['answer']}\n"
            for r in sr.get("results", [])[:3]:
                sr_text += f"• {r.get('title','')} ({r.get('url','')}): {r.get('content','')[:300]}\n"
            context_parts.append(sr_text)

    if dimension in ["perception", "campaigns"] and social_results:
        for sm in social_results[:5]:
            platform = sm.get("platform", "unknown")
            title = sm.get("title", "")
            content = sm.get("content", "")
            likes = sm.get("likes", 0)
            comments = sm.get("comments", 0)
            shares = sm.get("shares", 0)
            context_parts.append(
                f"=== Social Media ===\n平台: {platform}\n标题: {title}\n内容: {content}\n互动: 点赞{likes} 评论{comments} 分享{shares}\n"
            )

    combined = "\n".join(context_parts)
    if len(combined) < 500:
        for sr in search_results:
            sr_text = f"\n--- Search: {sr['query']} ---\n"
            if sr.get("answer"):
                sr_text += f"Answer: {sr['answer']}\n"
            for r in sr.get("results", [])[:5]:
                sr_text += f"• {r['title']} ({r['url']}): {r['content'][:300]}\n"
            if sr_text not in combined:
                context_parts.append(sr_text)
        combined = "\n".join(context_parts)

    if len(combined) > 8000:
        combined = combined[:8000] + "\n[...truncated...]"
    return combined


def _extract_dimension(
    dimension: str,
    dimension_schema: dict,
    context: str,
    url: str,
    clues: dict,
) -> dict:
    """Extract a single dimension using LLM with focused context."""
    from .templates import DIMENSION_TEMPLATES, validate_and_fix

    template = DIMENSION_TEMPLATES.get(dimension, {})
    template_text = json.dumps(template, ensure_ascii=False, indent=2)
    clues_text = json.dumps(clues, ensure_ascii=False, indent=2)

    prompt = f"""请根据以下品牌信息，填充这个JSON模板。尽可能多地从上下文中提取信息填入。

## 模板（按此结构填入值）：
{template_text}

## 规则：
1. 保持字段名和结构不变，只填入值
2. 尽量从上下文中提取信息填写每个字段——多填比少填好
3. 数组字段：找到多条就填多条
4. 如果上下文中能推断出信息，也要填写，加 [推断] 前缀
5. 只有完全找不到相关信息时才留空
6. 每条新闻、活动等信息尽量包含 source_url
7. 用中文填写，品牌名和专有名词可保留英文

## 品牌线索：
{clues_text}

## 上下文数据（网页、搜索结果、社交媒体）：
{context}

请直接输出填充后的JSON（不要包含任何解释）："""

    # 每个维度加具体例子，引导LLM正确输出
    DIMENSION_EXAMPLES = {
        "trust": """
## 输出示例：
{"certifications": ["ISO 9001", "B Corp认证"], "partnerships": ["与VF Corporation合作", "AMGA钻石合作伙伴"], "media_coverage": [{"outlet": "36氪", "title": "品牌获得新一轮融资", "date": "2024-06", "url": "https://..."}], "investor_backed": "VF Corporation（纽约证券交易所上市）", "user_stats": [{"metric": "全球门店", "value": "200+"}], "testimonials": [{"source": "行业专家", "quote": "该品牌在户外领域有标杆地位"}]}""",
        "experience": """
## 输出示例：
{"warranty": "产品提供一年质保", "return_policy": "30天无理由退换", "customer_service": {"channels": ["在线客服", "400电话", "门店"], "hours": "9:00-18:00"}, "faq": [{"question": "如何清洗冲锋衣？", "answer": "使用中性清洁剂手洗"}], "onboarding": "新用户注册即送会员积分", "community": "品牌社区活动、线下探索活动"}""",
        "vitality": """
## 输出示例（扁平JSON，不要type/properties）：
{"content_frequency": "每周2-3次社交媒体更新", "last_product_launch": "2024年9月 TNFH秋冬系列", "last_campaign": "2024年4月 天猫超级品牌日「山地节」", "growth_signal": "全球户外市场持续增长，品牌通过联名扩大潮流影响力", "community_size": "微博粉丝50万+", "nps_or_satisfaction": "[推断]用户评价普遍正面", "market_position": "全球TOP3户外品牌", "industry_role": "leader"}""",
        "campaigns": """
## 输出示例：
{"ongoing": [{"name": "Clothes the Loop", "type": "环保回收项目", "description": "鼓励消费者回收旧衣物", "start_date": "2013年"}], "recent": [{"name": "Supreme x TNF 2024联名", "type": "品牌联名", "date": "2024-03", "summary": "与Supreme推出春季联名系列", "source_url": "https://..."}], "upcoming": [], "annual_events": [{"name": "山地节", "frequency": "年度", "typical_month": "4月", "description": "天猫超级品牌日户外活动"}]}""",
        "content": """
## 输出示例：
{"latest_news": [{"title": "品牌宣布全面禁用皮草", "date": "2024-09", "summary": "VF集团宣布旗下所有品牌停止使用皮草和安哥拉山羊毛", "url": "https://...", "source_url": "https://..."}], "blog_posts": [{"title": "TNF vs Arc'teryx对比指南", "date": "2024-01", "summary": "两大户外品牌深度对比", "url": "https://..."}], "key_announcements": [], "brand_guidelines_public": ""}""",
    }
    
    if dimension in DIMENSION_EXAMPLES:
        prompt += DIMENSION_EXAMPLES[dimension]

    try:
        result = chat_json(
            prompt,
            system="你是品牌信息提取专家。按模板结构输出JSON。尽可能从上下文中提取信息填写每个字段，多填比少填好。不确定的信息加[推断]前缀。",
            max_tokens=4000,
            temperature=0.2,
        )
        result = validate_and_fix(dimension, result)
        return result
    except Exception as e:
        print(f"   ⚠️  Dimension {dimension} extraction failed: {e}")
        return dict(template)


def _normalize_result(result: dict) -> dict:
    """Final pass: ensure schema_version and offerings.items consistency."""
    off = result.get("offerings", {})
    if isinstance(off, dict) and "items" not in off:
        items = off.get("offerings", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            items = []
        result["offerings"] = {"items": items}
    return result


def structure_brand(
    url: str,
    pages: list[dict],
    clues: dict,
    search_results: list[dict],
    social_results: list[dict] = None,
) -> dict:
    """Combine all data and use LLM to produce final structured brand knowledge JSON."""
    print("🧠 Generating structured brand knowledge base...")

    if social_results is None:
        social_results = []

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    website_content = ""
    for p in pages:
        website_content += f"\n--- {p.get('url', '')} ---\n{p['content']}\n"

    search_content = ""
    for sr in search_results:
        search_content += f"\n--- Search: {sr['query']} ---\n"
        if sr.get("answer"):
            search_content += f"Answer: {sr['answer']}\n"
        for r in sr.get("results", [])[:5]:
            search_content += f"• {r['title']} ({r['url']}): {r['content'][:500]}\n"

    social_content = ""
    for sm in social_results:
        platform = sm.get("platform", "unknown")
        title = sm.get("title", "")
        content = sm.get("content", "")
        likes = sm.get("likes", 0)
        comments = sm.get("comments", 0)
        shares = sm.get("shares", 0)
        social_content += f"\n=== 社交媒体数据 ===\n平台: {platform}\n标题: {title}\n内容: {content}\n互动: 点赞{likes} 评论{comments} 分享{shares}\n"

    if len(website_content) > 25000:
        website_content = website_content[:25000] + "\n[...truncated...]"
    if len(search_content) > 10000:
        search_content = search_content[:10000] + "\n[...truncated...]"
    if len(social_content) > 8000:
        social_content = social_content[:8000] + "\n[...truncated...]"

    dimensions = [
        "identity",
        "offerings",
        "differentiation",
        "trust",
        "experience",
        "access",
        "content",
        "perception",
        "decision_factors",
        "vitality",
        "campaigns",
    ]

    def extract_one(dim: str) -> tuple[str, dict]:
        dim_schema = schema["properties"].get(dim, {"type": "object"})
        ctx = _select_context_for_dimension(
            dim, pages, search_results, social_results, clues
        )
        result = _extract_dimension(dim, dim_schema, ctx, url, clues)
        return dim, result

    dimension_results = {}
    failed_dims = []

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(extract_one, dim): dim for dim in dimensions}
            for future in as_completed(futures):
                dim, result = future.result()
                if result:
                    dimension_results[dim] = result
                    print(f"   ✅ {dim} extracted")
                else:
                    failed_dims.append(dim)
                    print(f"   ⚠️  {dim} failed")
    except Exception:
        pass

    if len(dimension_results) >= 9:
        final_result = {
            "schema_version": "0.4.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_urls": [url],
        }
        for dim in dimensions:
            if dim in dimension_results:
                final_result[dim] = dimension_results[dim]
        for dim in ["identity", "offerings", "access"]:
            if dim not in final_result:
                final_result[dim] = {}
        if "access" not in final_result:
            final_result["access"] = {}
        final_result["access"]["official_website"] = url
        if url not in final_result.get("source_urls", []):
            final_result.setdefault("source_urls", []).append(url)
        print("   ✅ Brand knowledge base generated (per-dimension)")
        return _normalize_result(final_result)

    print(
        f"   ⚠️  Per-dimension extraction incomplete ({len(dimension_results)}/11), falling back to full extraction..."
    )

    clues_text = json.dumps(clues, ensure_ascii=False, indent=2)
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)

    prompt = f"""You are a brand analyst creating a comprehensive brand knowledge base. 

Based on ALL the information provided below, generate a complete JSON object that matches the Brand Knowledge Schema v0.3.

## SCHEMA (you MUST follow this structure exactly):
{schema_text}

## RULES:
1. Fill EVERY field you can from the provided data. Leave out fields only if truly no data exists.
2. "schema_version" MUST be "0.4.0"
3. "generated_at" should be "{datetime.now(timezone.utc).isoformat()}"
4. "source_urls" should include "{url}"
5. "identity" and "offerings" are REQUIRED - always fill them
6. "access.official_website" MUST be "{url}"
7. For "offerings", create detailed entries for each product/service found
8. For "perception", infer brand personality from tone, messaging, and positioning
9. For "decision_factors", analyze what would matter to buyers in this category
10. For "vitality", assess how active/growing the brand appears
11. For "campaigns", fill ongoing (current campaigns), recent (past campaigns with impact), upcoming (announced future campaigns), and annual_events (recurring brand events). Look for product launches, promotions, collaborations, exhibitions, charity events, brand experiences.
12. For arrays of objects, include at least the required fields
13. CRITICAL: Never fabricate data. If the context does not contain information for a field, leave it empty (empty string or empty array). It is better to have missing data than false data.
14. Only use information explicitly present in the context. If inferred or uncertain, prefix the value with [推断].
15. Output ONLY valid JSON, no commentary

## EXTRACTED CLUES:
{clues_text}

## WEBSITE CONTENT:
{website_content}

## WEB SEARCH RESULTS:
{search_content if search_content.strip() else "(No search results available)"}

## SOCIAL MEDIA DATA (社交媒体数据):
{social_content if social_content.strip() else "(No social media data available)"}
注意：社交媒体数据对于填充 campaigns（品牌活动）、perception（公众认知）、trust（信任信号）维度特别有用。

Generate the complete brand knowledge JSON now:"""

    try:
        result = chat_json(
            prompt,
            system="You are a brand intelligence analyst. Output ONLY valid JSON matching the schema. Be thorough and precise. 请用中文填写所有字段内容。品牌名称、专有名词可保留英文原文。",
            max_tokens=16000,
        )
        result["schema_version"] = "0.4.0"
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        if "source_urls" not in result:
            result["source_urls"] = [url]
        if url not in result.get("source_urls", []):
            result.setdefault("source_urls", []).append(url)
        print("   ✅ Brand knowledge base generated (full)")
        return _normalize_result(result)
    except Exception as e:
        print(f"   ⚠️  Full extraction failed: {e}")
        print("   🔄 Using simplified fallback...")
        try:
            brand_name = clues.get("brand_name", "Unknown")
            retry_prompt = f"""Generate a brand knowledge JSON for "{brand_name}" (website: {url}).

Use this simplified structure:
{{
  "schema_version": "0.4.0",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "source_urls": ["{url}"],
  "identity": {{"name": "", "tagline": "", "positioning": "", "category": "", "founded": "", "headquarters": ""}},
  "offerings": [{{"name": "", "category": "", "description": "", "key_features": []}}],
  "differentiation": {{"unique_selling_points": [], "competitive_advantages": []}},
  "trust": {{"certifications": [], "partnerships": []}},
  "experience": {{}},
  "access": {{"official_website": "{url}"}},
  "content": {{}},
  "perception": {{"personality_traits": [], "brand_tone": "", "price_positioning": ""}},
  "decision_factors": {{}},
  "vitality": {{}},
  "campaigns": {{}}
}}

Available data:
{search_content[:5000] if search_content.strip() else website_content[:5000]}

Fill in as much as possible. Output ONLY valid JSON."""

            result = chat_json(
                retry_prompt,
                system="Output ONLY valid JSON. No explanation.",
                max_tokens=8000,
            )
            result["schema_version"] = "0.4.0"
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            result.setdefault("source_urls", [url])
            print("   ✅ Fallback succeeded")
            return _normalize_result(result)
        except Exception as e2:
            print(f"   ❌ Fallback also failed: {e2}")
            raise e


def _detect_affected_dimensions(changed_urls: list[str]) -> list[str]:
    """Detect which dimensions may be affected by changed URLs.

    Args:
        changed_urls: List of URLs that changed

    Returns:
        List of dimension names that may need regeneration
    """
    all_dimensions = [
        "identity",
        "offerings",
        "differentiation",
        "trust",
        "experience",
        "access",
        "content",
        "perception",
        "decision_factors",
        "vitality",
        "campaigns",
    ]

    if not changed_urls:
        return []

    affected: set[str] = set()

    for url in changed_urls:
        url_lower = url.lower()
        parsed = urlparse(url)
        path = parsed.path.lower() if parsed.path else ""

        is_homepage = (
            path == "/" or path == "" or url_lower.endswith("/") and path == ""
        )

        if is_homepage:
            affected.add("identity")
            affected.add("offerings")
            affected.add("access")
            continue

        for dimension, keywords in DIMENSION_CONTEXT_KEYWORDS.items():
            if any(kw in url_lower or kw in path for kw in keywords):
                affected.add(dimension)

    if not affected:
        return all_dimensions

    return list(affected)


def structure_brand_incremental(
    url: str,
    changed_pages: list[dict],
    all_pages: list[dict],
    clues: dict,
    search_results: list[dict],
    social_results: list[dict],
    previous_result: dict,
    changed_urls: list[str],
) -> dict:
    """Incrementally update brand knowledge base.

    Only regenerates dimensions affected by changed URLs.
    Unaffected dimensions are copied from previous_result.
    """
    from urllib.parse import urlparse

    print("🔄 Incremental brand knowledge base update...")

    if social_results is None:
        social_results = []

    affected_dimensions = _detect_affected_dimensions(changed_urls)
    unaffected_dimensions = [
        d
        for d in [
            "identity",
            "offerings",
            "differentiation",
            "trust",
            "experience",
            "access",
            "content",
            "perception",
            "decision_factors",
            "vitality",
            "campaigns",
        ]
        if d not in affected_dimensions
    ]

    print(
        f"   🔄 增量更新: 重新生成 {len(affected_dimensions)}/11 个维度, 复用 {len(unaffected_dimensions)} 个维度"
    )

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for dim in affected_dimensions:
            dim_schema = schema["properties"].get(dim, {"type": "object"})
            ctx = _select_context_for_dimension(
                dim,
                all_pages if all_pages else changed_pages,
                search_results,
                social_results,
                clues,
            )
            future = executor.submit(
                _extract_dimension, dim, dim_schema, ctx, url, clues
            )
            futures[future] = dim

        dimension_results = {}
        for future in as_completed(futures):
            dim = futures[future]
            try:
                result = future.result()
                if result:
                    dimension_results[dim] = result
                    print(f"   ✅ {dim} extracted")
                else:
                    dimension_results[dim] = previous_result.get(dim, {})
                    print(f"   ⚠️  {dim} failed, preserving previous")
            except Exception as e:
                dimension_results[dim] = previous_result.get(dim, {})
                print(f"   ⚠️  {dim} extraction error: {e}, preserving previous")

    final_result = {
        "schema_version": "0.4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_urls": list(set(previous_result.get("source_urls", []) + [url])),
    }

    for dim in unaffected_dimensions:
        if dim in previous_result:
            final_result[dim] = previous_result[dim]

    for dim in affected_dimensions:
        if dim in dimension_results:
            final_result[dim] = dimension_results[dim]
        elif dim in previous_result:
            final_result[dim] = previous_result[dim]

    for dim in ["identity", "offerings", "access"]:
        if dim not in final_result:
            final_result[dim] = previous_result.get(dim, {})

    if "access" not in final_result:
        final_result["access"] = {}
    final_result["access"]["official_website"] = url
    if url not in final_result.get("source_urls", []):
        final_result.setdefault("source_urls", []).append(url)

    print("   ✅ Incremental brand knowledge base generated")
    return _normalize_result(final_result)
