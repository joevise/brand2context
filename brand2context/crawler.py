"""Step 1: Website crawling via link2context API."""
import requests
from .config import LINK2CONTEXT_BASE, MAX_CRAWL_PAGES


def crawl_site(url: str) -> list[dict]:
    """Crawl a website and return list of {url, content} dicts."""
    print(f"🕷️  Crawling {url} (max {MAX_CRAWL_PAGES} pages)...")

    # Try crawl-site first
    try:
        resp = requests.post(
            f"{LINK2CONTEXT_BASE}/api/crawl-site",
            json={"pages": [url], "max_pages": MAX_CRAWL_PAGES},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        pages = data if isinstance(data, list) else data.get("pages", data.get("results", []))
        if pages:
            print(f"   ✅ Crawled {len(pages)} pages via crawl-site")
            return _normalize_pages(pages)
    except Exception as e:
        print(f"   ⚠️  crawl-site failed: {e}")

    # Fallback: convert single page
    try:
        print("   Trying /api/convert fallback...")
        resp = requests.post(
            f"{LINK2CONTEXT_BASE}/api/convert",
            json={"url": url},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data if isinstance(data, str) else data.get("content", data.get("markdown", str(data)))
        print(f"   ✅ Converted single page ({len(content)} chars)")
        return [{"url": url, "content": content}]
    except Exception as e:
        print(f"   ❌ Convert also failed: {e}")
        return []


def _normalize_pages(pages) -> list[dict]:
    """Normalize various response formats to [{url, content}]."""
    result = []
    for p in pages:
        if isinstance(p, dict):
            content = p.get("content", p.get("markdown", p.get("text", "")))
            page_url = p.get("url", p.get("page", ""))
            result.append({"url": page_url, "content": content})
        elif isinstance(p, str):
            result.append({"url": "", "content": p})
    return [r for r in result if r["content"]]
