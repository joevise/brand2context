"""Step 4: LLM structured extraction — the core of Brand2Context."""

import json
import os
from datetime import datetime, timezone
from .llm import chat_json
from .config import SCHEMA_PATH


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

    # Load schema
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    # Build context from all sources
    website_content = ""
    for p in pages:
        website_content += f"\n--- {p.get('url', '')} ---\n{p['content']}\n"

    search_content = ""
    for sr in search_results:
        search_content += f"\n--- Search: {sr['query']} ---\n"
        if sr.get("answer"):
            search_content += f"Answer: {sr['answer']}\n"
        for r in sr.get("results", []):
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

    clues_text = json.dumps(clues, ensure_ascii=False, indent=2)

    # Truncate to fit context
    max_website = 25000
    max_search = 10000
    max_social = 8000
    if len(website_content) > max_website:
        website_content = website_content[:max_website] + "\n[...truncated...]"
    if len(search_content) > max_search:
        search_content = search_content[:max_search] + "\n[...truncated...]"
    if len(social_content) > max_social:
        social_content = social_content[:max_social] + "\n[...truncated...]"

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
        # Ensure required fields
        result["schema_version"] = "0.3.0"
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        if "source_urls" not in result:
            result["source_urls"] = [url]
        if url not in result.get("source_urls", []):
            result.setdefault("source_urls", []).append(url)
        print("   ✅ Brand knowledge base generated")
        return result
    except Exception as e:
        print(f"   ❌ Structuring failed: {e}")
        raise
