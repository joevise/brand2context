"""Brand2Context CLI entry point."""
import json
import os
import re
import sys
from .config import OUTPUT_DIR
from .crawler import crawl_site
from .clue_extractor import extract_clues
from .web_searcher import search_expand
from .structurer import structure_brand


def slugify(name: str) -> str:
    """Convert brand name to safe filename."""
    if not name:
        return "unknown_brand"
    # Keep Chinese chars, alphanumeric, replace rest with underscore
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '_', name).strip('_').lower()
    return s or "unknown_brand"


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m brand2context <url>")
        print("Example: python -m brand2context https://www.example.com")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\n{'='*60}")
    print(f"🏢 Brand2Context — Building brand knowledge base")
    print(f"   Source: {url}")
    print(f"{'='*60}\n")

    # Step 1: Crawl
    pages = crawl_site(url)

    # Step 2: Extract clues
    clues = extract_clues(pages, url)

    # Step 3: Web search expansion
    search_results = search_expand(clues)

    # Step 4: Structure
    if not pages and not search_results:
        print("\n❌ No data collected. Cannot generate knowledge base.")
        sys.exit(1)

    result = structure_brand(url, pages, clues, search_results)

    # Save output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    brand_name = clues.get("brand_name", "") or result.get("identity", {}).get("name", "unknown")
    filename = slugify(brand_name) + ".json"
    output_path = os.path.join(OUTPUT_DIR, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Brand knowledge base saved to: {output_path}")
    print(f"   Brand: {result.get('identity', {}).get('name', 'N/A')}")
    print(f"   Offerings: {len(result.get('offerings', []))} items")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
