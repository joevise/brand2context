"""Brand2Context CLI entry point.

Default pipeline (v2): Goal-Driven BrandResearcher Agent (single-agent ReAct loop)
Legacy pipeline (v1): crawl_site → extract_clues → search_expand → structure_brand
                      Use --legacy flag to opt in.
"""
import json
import os
import re
import sys
from .config import OUTPUT_DIR


def slugify(name: str) -> str:
    """Convert brand name to safe filename."""
    if not name:
        return "unknown_brand"
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '_', name).strip('_').lower()
    return s or "unknown_brand"


def _infer_brand_name_from_url(url: str) -> str:
    """Best-effort: extract brand name from domain (e.g. nike.com → Nike)."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.replace("www.", "")
    base = host.split(".")[0]
    return base.capitalize() if base else "unknown"


def run_v1(url: str):
    """Legacy pipeline."""
    from .crawler import crawl_site
    from .clue_extractor import extract_clues
    from .web_searcher import search_expand
    from .structurer import structure_brand

    print(f"\n{'=' * 60}\n🏢 Brand2Context v1 (legacy)\n   Source: {url}\n{'=' * 60}\n")
    pages = crawl_site(url)
    clues = extract_clues(pages, url)
    search_results = search_expand(clues)
    if not pages and not search_results:
        print("\n❌ No data collected.")
        sys.exit(1)
    result = structure_brand(url, pages, clues, search_results)
    brand_name = clues.get("brand_name", "") or result.get("identity", {}).get("name", "unknown")
    out_dir = OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, slugify(brand_name) + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved to: {out_path}")


def run_v2(url: str, name: str, category: str, max_rounds: int):
    """Default v2 pipeline — Agent ReAct loop."""
    from .v2.researcher import run_researcher
    return run_researcher(url, name, category, max_rounds=max_rounds)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Brand2Context — build brand knowledge base")
    ap.add_argument("url", help="Brand homepage URL")
    ap.add_argument("--name", help="Brand name (default: inferred from domain)")
    ap.add_argument("--category", default="未分类", help="Brand category hint")
    ap.add_argument("--max-rounds", type=int, default=30, help="v2 only: max agent decision rounds")
    ap.add_argument("--legacy", action="store_true", help="Use v1 legacy pipeline")
    args = ap.parse_args()

    url = args.url if args.url.startswith("http") else "https://" + args.url

    if args.legacy:
        run_v1(url)
    else:
        name = args.name or _infer_brand_name_from_url(url)
        run_v2(url, name, args.category, args.max_rounds)


if __name__ == "__main__":
    main()
