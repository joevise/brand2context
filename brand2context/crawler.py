"""Step 1: Website crawling via link2context API."""

import hashlib
import json
import re
import subprocess
import tempfile
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


def _convert_page_playwright(url: str) -> dict | None:
    """Convert a single page using Playwright (headless Chromium).

    This is a fallback when link2context API fails or returns insufficient content.
    Uses subprocess to run Playwright in a separate process.
    """
    script = """
import asyncio
from playwright.async_api import async_playwright
import json, sys

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto(sys.argv[1], wait_until="networkidle", timeout=30000)
        title = await page.title()
        text = await page.evaluate("() => document.body.innerText")
        await browser.close()
        print(json.dumps({"title": title, "content": text, "url": sys.argv[1]}))

asyncio.run(main())
"""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=True) as f:
            f.write(script)
            script_path = f.name

        result = subprocess.run(
            ["python3", script_path, url],
            capture_output=True,
            text=True,
            timeout=45,
        )

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "url": data.get("url", url),
                "title": data.get("title", ""),
                "content": data.get("content", ""),
            }
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Playwright timeout for {url}")
    except Exception as e:
        print(f"   ⚠️ Playwright failed for {url}: {e}")

    return None


def _convert_page(url: str) -> dict | None:
    """Convert a single page via link2context API with Playwright fallback."""
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

        if len(content) < 200:
            print(
                f"   ⚠️ link2context returned too little content for {url}, trying Playwright..."
            )
            pw_result = _convert_page_playwright(url)
            if pw_result:
                return pw_result

        return {"url": url, "title": title, "content": content}
    except Exception:
        print(f"   ⚠️ link2context failed, trying Playwright...")
        return _convert_page_playwright(url)


def crawl_site(url: str) -> list[dict]:
    """Crawl a website and return list of {url, content} dicts."""
    print(f"🕷️  Crawling {url} (max {MAX_CRAWL_PAGES} pages)...")

    sitemap_urls = _parse_sitemap(url)
    sitemap_count = len(sitemap_urls)
    print(f"   📋 Sitemap found {sitemap_count} URLs")

    main_page = _convert_page(url)
    if not main_page:
        print("   ❌ Failed to crawl main page via link2context")
        all_urls = [
            (u["url"], _score_page(u["url"], u.get("priority", 0.5)))
            for u in sitemap_urls[:10]
        ]
        if not all_urls:
            return []

        print(
            f"   🔄 Trying Playwright on top {min(5, len(all_urls))} high-priority URLs..."
        )
        pages = []
        pw_success = 0
        for u, score in all_urls[:5]:
            page = _convert_page_playwright(u)
            if page and len(page["content"]) > 100:
                pages.append(page)
                pw_success += 1
                print(f"   ✅ [PW] {page['title'][:40]} ({len(page['content'])} chars)")

        print(f"   📊 link2context: 0 pages, Playwright: {pw_success} pages")
        return pages

    pages = [main_page]
    print(f"   ✅ Main page: {main_page['title']} ({len(main_page['content'])} chars)")

    internal_links = _extract_internal_links(url, main_page["content"])
    internal_links_count = len(internal_links)
    print(f"   🔗 Found {internal_links_count} internal links")

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

    all_urls.sort(key=lambda x: x[1], reverse=True)

    link2context_success = 1
    for u, score in all_urls:
        if len(pages) >= MAX_CRAWL_PAGES:
            break
        if u == url:
            continue

        page = _convert_page(u)
        if page and len(page["content"]) > 100:
            pages.append(page)
            link2context_success += 1
            print(
                f"   ✅ [{score:.2f}] {page['title'][:40]} ({len(page['content'])} chars)"
            )

    print(f"   📄 Total: {len(pages)} pages (link2context: {link2context_success})")
    return pages


def _compute_content_hash(content: str) -> str:
    """Compute md5 hash of content string."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def crawl_site_incremental(
    url: str, previous_hashes: dict[str, str] = None
) -> tuple[list[dict], dict[str, str], list[str]]:
    """Crawl site incrementally, returning only changed pages.

    Args:
        url: The base URL to crawl
        previous_hashes: Dict of URL -> content hash from previous crawl

    Returns:
        Tuple of (changed_pages, current_hashes, changed_urls)
        - changed_pages: list of page dicts with changes
        - current_hashes: dict of all URL -> hash for this crawl
        - changed_urls: list of URLs that changed
    """
    if previous_hashes is None:
        previous_hashes = {}

    print(f"🕷️  Incremental crawl of {url} (max {MAX_CRAWL_PAGES} pages)...")

    sitemap_urls = _parse_sitemap(url)
    sitemap_count = len(sitemap_urls)
    print(f"   📋 Sitemap found {sitemap_count} URLs")

    main_page = _convert_page(url)
    if not main_page:
        print("   ❌ Failed to crawl main page via link2context")
        all_urls = [
            (u["url"], _score_page(u["url"], u.get("priority", 0.5)))
            for u in sitemap_urls[:10]
        ]
        if not all_urls:
            return [], {}, []

        print(
            f"   🔄 Trying Playwright on top {min(5, len(all_urls))} high-priority URLs..."
        )
        pages = []
        pw_success = 0
        for u, score in all_urls[:5]:
            page = _convert_page_playwright(u)
            if page and len(page["content"]) > 100:
                pages.append(page)
                pw_success += 1
                print(f"   ✅ [PW] {page['title'][:40]} ({len(page['content'])} chars)")

        print(f"   📊 link2context: 0 pages, Playwright: {pw_success} pages")
        current_hashes = {p["url"]: _compute_content_hash(p["content"]) for p in pages}
        changed_urls = []
        for p in pages:
            if (
                p["url"] not in previous_hashes
                or previous_hashes[p["url"]] != current_hashes[p["url"]]
            ):
                changed_urls.append(p["url"])
        changed_pages = [p for p in pages if p["url"] in changed_urls]
        unchanged_count = len(pages) - len(changed_pages)
        new_count = len([u for u in changed_urls if u not in previous_hashes])
        print(
            f"📊 增量检测: {unchanged_count} 页未变化, {len(changed_urls) - new_count} 页有更新, {new_count} 页新增"
        )
        return changed_pages, current_hashes, changed_urls

    pages = [main_page]
    print(f"   ✅ Main page: {main_page['title']} ({len(main_page['content'])} chars)")

    internal_links = _extract_internal_links(url, main_page["content"])
    internal_links_count = len(internal_links)
    print(f"   🔗 Found {internal_links_count} internal links")

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

    all_urls.sort(key=lambda x: x[1], reverse=True)

    link2context_success = 1
    for u, score in all_urls:
        if len(pages) >= MAX_CRAWL_PAGES:
            break
        if u == url:
            continue

        page = _convert_page(u)
        if page and len(page["content"]) > 100:
            pages.append(page)
            link2context_success += 1
            print(
                f"   ✅ [{score:.2f}] {page['title'][:40]} ({len(page['content'])} chars)"
            )

    print(f"   📄 Total: {len(pages)} pages (link2context: {link2context_success})")

    current_hashes = {p["url"]: _compute_content_hash(p["content"]) for p in pages}
    changed_urls = []
    for p in pages:
        if (
            p["url"] not in previous_hashes
            or previous_hashes[p["url"]] != current_hashes[p["url"]]
        ):
            changed_urls.append(p["url"])
    changed_pages = [p for p in pages if p["url"] in changed_urls]
    unchanged_count = len(pages) - len(changed_pages)
    new_count = len([u for u in changed_urls if u not in previous_hashes])
    updated_count = len(changed_urls) - new_count
    print(
        f"📊 增量检测: {unchanged_count} 页未变化, {updated_count} 页有更新, {new_count} 页新增"
    )

    return changed_pages, current_hashes, changed_urls


def _extract_internal_links(base_url: str, markdown_content: str) -> list[str]:
    """Extract internal links from markdown content."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
    matches = re.findall(link_pattern, markdown_content)

    internal_links = []
    seen = set()

    for text, href in matches:
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        if "/api/" in href or href.endswith(
            (".png", ".jpg", ".svg", ".gif", ".css", ".js")
        ):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc and parsed.netloc != base_domain:
            continue

        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url.endswith("/"):
            clean_url = clean_url[:-1]
        if clean_url not in seen and clean_url != base_url.rstrip("/"):
            seen.add(clean_url)
            internal_links.append(clean_url)

    return internal_links
