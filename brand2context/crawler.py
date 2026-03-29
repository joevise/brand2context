"""Step 1: Website crawling via link2context API."""
import re
import requests
from urllib.parse import urljoin, urlparse
from .config import LINK2CONTEXT_BASE, MAX_CRAWL_PAGES


def crawl_site(url: str) -> list[dict]:
    """Crawl a website and return list of {url, content} dicts."""
    print(f"🕷️  Crawling {url} (max {MAX_CRAWL_PAGES} pages)...")

    # Step 1: Convert the main page first
    main_page = _convert_page(url)
    if not main_page:
        print("   ❌ Failed to crawl main page")
        return []

    pages = [main_page]
    print(f"   ✅ Main page: {main_page['title']} ({len(main_page['content'])} chars)")

    # Step 2: Extract internal links from main page content
    internal_links = _extract_internal_links(url, main_page["content"])
    if internal_links:
        print(f"   🔗 Found {len(internal_links)} internal links, crawling...")

    # Step 3: Crawl each internal link (up to MAX_CRAWL_PAGES)
    crawled_urls = {url}
    for link in internal_links:
        if len(pages) >= MAX_CRAWL_PAGES:
            break
        if link in crawled_urls:
            continue
        crawled_urls.add(link)

        page = _convert_page(link)
        if page and len(page["content"]) > 100:  # Skip near-empty pages
            pages.append(page)
            print(f"   ✅ {page['title'][:40]} ({len(page['content'])} chars)")

    print(f"   📄 Total: {len(pages)} pages crawled")
    return pages


def _convert_page(url: str) -> dict | None:
    """Convert a single page via link2context API."""
    try:
        resp = requests.post(
            f"{LINK2CONTEXT_BASE}/api/convert",
            json={"url": url},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            return None
        content = data.get("markdown", "")
        title = data.get("title", url)
        return {"url": url, "title": title, "content": content}
    except Exception:
        return None


def _extract_internal_links(base_url: str, markdown_content: str) -> list[str]:
    """Extract internal links from markdown content."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    # Find all markdown links: [text](url) and bare URLs
    link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(link_pattern, markdown_content)

    internal_links = []
    seen = set()

    for text, href in matches:
        # Skip anchors, images, external links, API paths
        if href.startswith('#') or href.startswith('mailto:'):
            continue
        if '/api/' in href or href.endswith(('.png', '.jpg', '.svg', '.gif', '.css', '.js')):
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only keep same-domain links
        if parsed.netloc and parsed.netloc != base_domain:
            continue

        # Normalize
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url.endswith('/'):
            clean_url = clean_url[:-1]
        if clean_url not in seen and clean_url != base_url.rstrip('/'):
            seen.add(clean_url)
            internal_links.append(clean_url)

    return internal_links
