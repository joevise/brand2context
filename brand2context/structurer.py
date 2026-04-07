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
        if not sr_keywords or any(kw in query_lower for kw in sr_keywords):
            sr_text = f"\n--- Search: {sr['query']} ---\n"
            if sr.get("answer"):
                sr_text += f"Answer: {sr['answer']}\n"
            for r in sr.get("results", [])[:3]:
                sr_text += f"• {r['title']} ({r['url']}): {r['content'][:300]}\n"
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
    schema_text = json.dumps(dimension_schema, ensure_ascii=False, indent=2)
    clues_text = json.dumps(clues, ensure_ascii=False, indent=2)

    prompt = f"""You are a brand analyst extracting the "{dimension}" dimension of a brand knowledge base.

## {dimension.upper()} SCHEMA:
{schema_text}

## RULES:
1. Fill in as many fields as possible from the provided context
2. "schema_version" MUST be "0.3.0"
3. For arrays, include at least the key fields
4. Output ONLY valid JSON matching the schema above
5. If insufficient data, output an empty object or minimal valid structure

## BRAND CLUES:
{clues_text}

## CONTEXT (relevant pages, search results, social data):
{context}

Generate the {dimension} JSON now:"""

    try:
        result = chat_json(
            prompt,
            system="You are a brand intelligence analyst. Output ONLY valid JSON matching the schema. Be thorough and precise. 请用中文填写所有字段内容。品牌名称、专有名词可保留英文原文。",
            max_tokens=4000,
        )
        return result
    except Exception as e:
        print(f"   ⚠️  Dimension {dimension} extraction failed: {e}")
        return {}


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
            "schema_version": "0.3.0",
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
        return final_result

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
2. "schema_version" MUST be "0.3.0"
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
13. Output ONLY valid JSON, no commentary

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
        result["schema_version"] = "0.3.0"
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        if "source_urls" not in result:
            result["source_urls"] = [url]
        if url not in result.get("source_urls", []):
            result.setdefault("source_urls", []).append(url)
        print("   ✅ Brand knowledge base generated (full)")
        return result
    except Exception as e:
        print(f"   ⚠️  Full extraction failed: {e}")
        print("   🔄 Using simplified fallback...")
        try:
            brand_name = clues.get("brand_name", "Unknown")
            retry_prompt = f"""Generate a brand knowledge JSON for "{brand_name}" (website: {url}).

Use this simplified structure:
{{
  "schema_version": "0.3.0",
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
            result["schema_version"] = "0.3.0"
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            result.setdefault("source_urls", [url])
            print("   ✅ Fallback succeeded")
            return result
        except Exception as e2:
            print(f"   ❌ Fallback also failed: {e2}")
            raise e
