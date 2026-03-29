"""Step 2: LLM-based clue extraction from crawled content."""
from .llm import chat_json


def extract_clues(pages: list[dict], url: str) -> dict:
    """Extract brand clues from crawled pages using LLM."""
    print("🔍 Extracting clues from crawled content...")

    # Combine page content (truncate to ~30k chars to fit context)
    combined = ""
    for p in pages:
        page_url = p.get("url", "")
        combined += f"\n\n--- Page: {page_url} ---\n{p['content']}"
        if len(combined) > 30000:
            break

    if not combined.strip():
        print("   ⚠️  No content to extract clues from, using URL only")
        return {"source_url": url, "brand_name": "", "clues_extracted": False}

    prompt = f"""Analyze the following website content and extract brand clues. Return a JSON object with these fields:

- brand_name: string (the brand/company name)
- legal_name: string (legal/registered company name if found)
- tagline: string
- category: string (what industry/category)
- founder: string (founder name if found)
- founded: string (year founded if found)
- headquarters: string
- social_media: list of {{"platform": "...", "url": "..."}} (WeChat, Weibo, Douyin, Xiaohongshu, Twitter, LinkedIn, etc.)
- partners: list of strings (partner/client company names)
- ecommerce_links: list of {{"platform": "...", "url": "..."}}
- media_links: list of {{"title": "...", "url": "..."}}
- contact: {{"phone": "...", "email": "...", "address": "..."}}
- products: list of strings (product/service names found)
- key_claims: list of strings (key marketing claims or value propositions)

Only include fields where you found actual data. If not found, use empty string or empty list.

Source URL: {url}

Website content:
{combined[:30000]}"""

    try:
        clues = chat_json(prompt, system="You are a brand analyst. Extract factual information only. Return valid JSON.")
        clues["source_url"] = url
        clues["clues_extracted"] = True
        brand = clues.get("brand_name", "")
        print(f"   ✅ Extracted clues for brand: {brand}")
        return clues
    except Exception as e:
        print(f"   ❌ Clue extraction failed: {e}")
        return {"source_url": url, "brand_name": "", "clues_extracted": False}
