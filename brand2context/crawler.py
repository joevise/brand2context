"""Step 1: Website crawling via link2context API."""

import re
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urljoin, urlparse
from .config import LINK2CONTEXT_BASE, MAX_CRAWL_PAGES

HIGH_VALUE_KEYWORDS = [
    "about",
    "team",
    "product",
    "service",
    "pricing",
    "contact",
    "story",
    "history",
    "mission",
    "vision",
    "career",
    "investor",
    "partnership",
    "press",
    "news",
    "blog",
]
LOW_VALUE_KEYWORDS = [
    "privacy",
    "policy",
    "legal",
    "terms",
    "cookie",
    "disclaimer",
    "sitemap",
    "login",
    "register",
    "cart",
    "checkout",
    "404",
    "print",
    "xml",
    "rss",
    "feed",
]


def _parse_sitemap(url: str) -> list[dict]:
    """Parse sitemap.xml and return list of URL metadata dicts."""
    sitemap_url = url.rstrip("/") + "/sitemap.xml"
    try:
        resp = requests.get(sitemap_url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []

        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall("sm:sitemap", ns):
                loc = sitemap.find("sm:loc", ns)
                if loc is not None and loc.text:
                    sub_urls = _parse_sitemap(loc.text)
                    urls.extend(sub_urls)
        else:
            for url_elem in root.findall("sm:url", ns):
                loc = url_elem.find("sm:loc", ns)
                if loc is None or not loc.text:
                    continue
                priority = url_elem.find("sm:priority", ns)
                lastmod = url_elem.find("sm:lastmod", ns)
                changefreq = url_elem.find("sm:changefreq", ns)
                urls.append(
                    {
                        "url": loc.text.strip(),
                        "priority": float(priority.text)
                        if priority is not None and priority.text
                        else 0.5,
                        "lastmod": lastmod.text if lastmod is not None else "",
                        "changefreq": changefreq.text if changefreq is not None else "",
                    }
                )

        return urls
    except Exception:
        return []


def _score_page(url: str, sitemap_priority: float = 0.5) -> float:
    """Score a page URL based on keywords and sitemap priority."""
    url_lower = url.lower()
    score = sitemap_priority
    if any(kw in url_lower for kw in HIGH_VALUE_KEYWORDS):
        score += 0.3
    if any(kw in url_lower for kw in LOW_VALUE_KEYWORDS):
        score -= 0.5
    return max(0.0, min(1.0, score))


def crawl_site(url: str) -> list[dict]:
    """Crawl a website and return list of {url, content} dicts."""
    print(f"🕷️  Crawling {url} (max {MAX_CRAWL_PAGES} pages)...")

    # Step 1: Try parsing sitemap.xml for full site URL list
    sitemap_urls = _parse_sitemap(url)
    sitemap_count = len(sitemap_urls)
    print(f"   📋 Sitemap found {sitemap_count} URLs")

    # Step 2: Convert main page first
    main_page = _convert_page(url)
    if not main_page:
        print("   ❌ Failed to crawl main page")
        return []

    pages = [main_page]
    print(f"   ✅ Main page: {main_page['title']} ({len(main_page['content'])} chars)")

    # Step 3: Extract internal links from main page content
    internal_links = _extract_internal_links(url, main_page["content"])
    internal_links_count = len(internal_links)
    print(f"   🔗 Found {internal_links_count} internal links")

    # Step 4: Merge and deduplicate (sitemap + internal links)
    all_urls = []
    seen = {url}

    for sm_url in sitemap_urls:
        u = sm_url["url"]
        if u not in seen:
            seen.add(u)
            score = _score_page(u, sm_url.get("priority", 0.5))
            all_urls.append((u, score))

    for link in internal_links:
        if link not in seen:
            seen.add(link)
            all_urls.append((link, _score_page(link)))

    merged_count = len(all_urls)
    print(
        f"   🔄 Merged total: {merged_count} URLs (sitemap: {sitemap_count}, internal: {internal_links_count})"
    )

    # Step 5: Sort by priority score descending
    all_urls.sort(key=lambda x: x[1], reverse=True)

    # Step 6: Crawl top pages up to MAX_CRAWL_PAGES
    for u, score in all_urls:
        if len(pages) >= MAX_CRAWL_PAGES:
            break
        if u == url:
            continue

        page = _convert_page(u)
        if page and len(page["content"]) > 100:
            pages.append(page)
            print(
                f"   ✅ [{score:.2f}] {page['title'][:40]} ({len(page['content'])} chars)"
            )

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
    link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
    matches = re.findall(link_pattern, markdown_content)

    internal_links = []
    seen = set()

    for text, href in matches:
        # Skip anchors, images, external links, API paths
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        if "/api/" in href or href.endswith(
            (".png", ".jpg", ".svg", ".gif", ".css", ".js")
        ):
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only keep same-domain links
        if parsed.netloc and parsed.netloc != base_domain:
            continue

        # Normalize
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url.endswith("/"):
            clean_url = clean_url[:-1]
        if clean_url not in seen and clean_url != base_url.rstrip("/"):
            seen.add(clean_url)
            internal_links.append(clean_url)

    return internal_links
