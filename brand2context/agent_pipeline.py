"""Agent Pipeline — LLM-driven crawl loop with self-assessment."""

import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from .raw_store import RawStore
from .judge import judge_completeness
from .crawler import (
    crawl_site,
    _convert_page,
    _parse_sitemap,
    _score_page,
    explore_site,
)
from .web_searcher import search_expand, _search_metaso, _search_tavily, _is_china_brand
from .clue_extractor import extract_clues
from .structurer import (
    structure_brand,
    _extract_dimension,
    _select_context_for_dimension,
    DIMENSION_CONTEXT_KEYWORDS,
)
from .llm import chat_json
from .config import SCHEMA_PATH, MAX_CRAWL_PAGES

MAX_ROUNDS = 6
PIPELINE_TIMEOUT = 900


def _inject_strategy_actions(
    gaps: list, scores: dict, round_num: int, brand_name: str, url: str
) -> list:
    """Inject smart actions when LLM judge fails to use explore/deep_search."""
    existing_actions = {g.get("action") for g in gaps}
    existing_dims_with_explore = {
        g.get("dimension") for g in gaps if g.get("action") == "explore"
    }

    injected = []

    # offerings: if score < 5 (on 0-10 scale) and round >= 2
    if (
        scores.get("offerings", 10) < 5
        and round_num >= 2
        and "offerings" not in existing_dims_with_explore
    ):
        injected.append(
            {
                "dimension": "offerings",
                "missing": "auto: explore products",
                "action": "explore",
                "target_type": "products",
            }
        )

    # content: if score < 5 and round >= 2
    if (
        scores.get("content", 10) < 5
        and round_num >= 2
        and "content" not in existing_dims_with_explore
    ):
        injected.append(
            {
                "dimension": "content",
                "missing": "auto: explore news",
                "action": "explore",
                "target_type": "news",
            }
        )

    # trust: if score < 5 and round >= 2
    if (
        scores.get("trust", 10) < 5
        and round_num >= 2
        and "deep_search" not in existing_actions
    ):
        injected.append(
            {
                "dimension": "trust",
                "missing": "auto: deep search partners",
                "action": "deep_search",
                "query": f"{brand_name} 合作伙伴 认证 partnerships certifications",
            }
        )

    # experience: if score < 5 and round >= 2
    if (
        scores.get("experience", 10) < 5
        and round_num >= 2
        and "experience" not in existing_dims_with_explore
    ):
        injected.append(
            {
                "dimension": "experience",
                "missing": "auto: explore faq",
                "action": "explore",
                "target_type": "faq",
            }
        )

    # campaigns: if score < 5 and round >= 2
    if (
        scores.get("campaigns", 10) < 5
        and round_num >= 2
    ):
        injected.append(
            {
                "dimension": "campaigns",
                "missing": "auto: deep search campaigns",
                "action": "deep_search",
                "query": f"{brand_name} 2024 2025 活动 campaign event 新品发布",
            }
        )

    if injected:
        print(f"   [STRATEGY] Injected {len(injected)} smart actions:")
        for inj in injected:
            print(
                f"      -> {inj['action']}: {inj['dimension']} ({inj.get('target_type', inj.get('query', '')[:30])})"
            )
    else:
        print(f"   [STRATEGY] No injection needed (scores: {dict(list(scores.items())[:5])}...)")

    # Put injected actions FIRST so they execute before the original search-only gaps
    return injected + gaps


def run_agent_pipeline(
    brand_id: str,
    url: str,
    brand_name: str = "",
    category: str = "",
    data_dir: str = "data/brands",
) -> dict:
    """Run the full agent pipeline for a brand.

    Args:
        brand_id: UUID of the brand
        url: Brand website URL
        brand_name: Known brand name (optional)
        category: Known category (optional)
        data_dir: Base directory for raw data storage

    Returns:
        Complete brand knowledge JSON
    """
    start_time = time.time()
    store = RawStore(brand_id, base_dir=data_dir)

    print(f"🤖 Agent Pipeline starting for {brand_name or url}")

    # ========== Round 1: Initial Crawl ==========
    print(f"\n{'=' * 50}")
    print(f"📡 Round 1: Initial crawl")
    print(f"{'=' * 50}")

    pages = crawl_site(url)
    pages_added = 0
    for p in pages:
        store.add_page(
            p["url"], p.get("title", ""), p["content"], source="link2context"
        )
        pages_added += 1

    if not pages:
        print(f"⚠️ Crawl failed, trying Metaso Reader...")
        from .web_searcher import metaso_read_url

        content = metaso_read_url(url)
        if content and len(content) > 100:
            store.add_page(url, "Homepage (Metaso)", content, source="metaso_reader")
            pages = [{"url": url, "content": content}]
            pages_added = 1

    clues = extract_clues(pages, url)
    if not clues.get("brand_name") and brand_name:
        clues["brand_name"] = brand_name
    if not clues.get("category") and category:
        clues["category"] = category
    actual_brand_name = clues.get("brand_name", brand_name or "")
    actual_category = clues.get("category", category or "")

    search_results = search_expand(clues, pages=pages)
    searches_added = 0
    for sr in search_results:
        source = sr.get("source", "tavily")
        store.add_search_result(
            sr["query"],
            sr.get("results", []),
            source=source,
            answer=sr.get("answer", ""),
        )
        searches_added += 1

    store.update_manifest(1, "initial_crawl", pages_added, searches_added)
    print(f"📊 Round 1 complete: {pages_added} pages, {searches_added} searches stored")

    # ========== Rounds 2-N: Judge + Fill Loop ==========
    prev_data_count = pages_added + searches_added

    for round_num in range(2, MAX_ROUNDS + 2):
        elapsed = time.time() - start_time
        if elapsed > PIPELINE_TIMEOUT:
            print(f"⏰ Pipeline timeout ({elapsed:.0f}s), proceeding to generation")
            break

        print(f"\n{'=' * 50}")
        print(f"🔍 Round {round_num}: LLM Assessment")
        print(f"{'=' * 50}")

        summary = store.get_summary()

        judgment = judge_completeness(actual_brand_name, url, actual_category, summary)

        overall = judgment.get("overall_score", 0)
        is_sufficient = judgment.get("is_sufficient", False)
        gaps = judgment.get("gaps", [])
        scores = judgment.get("scores", {})

        print(f"📊 Overall score: {overall}/10")
        for dim, score in sorted(scores.items(), key=lambda x: x[1]):
            emoji = "✅" if score >= 7 else "⚠️" if score >= 4 else "❌"
            print(f"   {emoji} {dim}: {score}/10")

        if is_sufficient:
            print(f"✅ Data is sufficient! Proceeding to final generation.")
            store.update_manifest(
                round_num, "assessment_passed", 0, 0, reason="All dimensions sufficient"
            )
            break

        if round_num > MAX_ROUNDS + 1:
            print(f"⏹ Max rounds reached, proceeding with available data")
            break

        # Strategy layer: auto-inject explore/deep_search when LLM fails to
        gaps = _inject_strategy_actions(gaps, scores, round_num, actual_brand_name, url)
        print(f"\n🔧 Filling {len(gaps)} gaps...")
        new_pages = 0
        new_searches = 0

        for gap in gaps[:12]:
            action = gap.get("action", "")
            dimension = gap.get("dimension", "")

            if action == "search":
                query = gap.get("query", "")
                if not query:
                    continue
                print(f'   🔎 Search: "{query}" (for {dimension})')
                is_china = _is_china_brand(url, actual_brand_name)
                if is_china:
                    sr = _search_metaso(query, size=5)
                else:
                    sr = _search_tavily(query, max_results=5)
                if sr.get("results"):
                    store.add_search_result(
                        query,
                        sr["results"],
                        source=sr.get("source", "tavily"),
                        answer=sr.get("answer", ""),
                    )
                    new_searches += 1
                    print(f"      ✅ {len(sr['results'])} results stored")
                else:
                    print(f"      ⚠️ No results")

            elif action == "crawl":
                target = gap.get("target", "")
                if not target:
                    continue
                if target.startswith("/"):
                    crawl_url = urljoin(url, target)
                elif target.startswith("http"):
                    crawl_url = target
                else:
                    crawl_url = urljoin(url, "/" + target)

                print(f"   🕷️ Crawl: {crawl_url} (for {dimension})")
                page = _convert_page(crawl_url, force_dynamic=True)
                if page and len(page.get("content", "")) > 100:
                    store.add_page(
                        page["url"],
                        page.get("title", ""),
                        page["content"],
                        source="gap_fill",
                    )
                    new_pages += 1
                    print(f"      ✅ {len(page['content'])} chars stored")
                else:
                    print(f"      ⚠️ Crawl failed or empty")

            elif action == "explore":
                target_type = gap.get("target_type", "products")
                print(f"   🧭 Explore: {url} for {target_type} (for {dimension})")
                pages = explore_site(url, target_type)
                for page in pages:
                    store.add_page(
                        page["url"],
                        page.get("title", ""),
                        page["content"],
                        source="gap_fill_explore",
                    )
                    new_pages += 1
                if pages:
                    print(f"      ✅ {len(pages)} pages stored")
                else:
                    print(f"      ⚠️ No pages found")

            elif action == "deep_search":
                query = gap.get("query", "")
                if not query:
                    continue
                print(f'   🔍 Deep Search: "{query}" (for {dimension})')
                metaso_results = _search_metaso(query, size=5)
                tavily_results = _search_tavily(query, max_results=5)

                all_results = []
                if metaso_results.get("results"):
                    all_results.extend(metaso_results["results"])
                if tavily_results.get("results"):
                    all_results.extend(tavily_results["results"])

                if all_results:
                    store.add_search_result(
                        query,
                        all_results,
                        source="deep_search",
                        answer=metaso_results.get("answer", "")
                        or tavily_results.get("answer", ""),
                    )
                    new_searches += 1
                    print(f"      ✅ {len(all_results)} combined results stored")

                    for r in all_results[:5]:
                        r_url = r.get("url", "")
                        if r_url and r_url.startswith("http"):
                            page = _convert_page(r_url, force_dynamic=True)
                            if page and len(page.get("content", "")) > 100:
                                store.add_page(
                                    page["url"],
                                    page.get("title", ""),
                                    page["content"],
                                    source="deep_search_crawl",
                                )
                                new_pages += 1
                    if new_pages > 0:
                        print(f"      ✅ Auto-crawled {new_pages} result pages")
                else:
                    print(f"      ⚠️ No results")

        store.update_manifest(
            round_num,
            "gap_fill",
            new_pages,
            new_searches,
            reason="; ".join([f"{g['dimension']}: {g['missing']}" for g in gaps[:3]]),
        )

        current_data_count = (
            store.get_summary()["total_pages"] + store.get_summary()["total_searches"]
        )
        if current_data_count == prev_data_count:
            print(f"⏹ No new data added this round, stopping loop")
            break
        prev_data_count = current_data_count

        print(
            f"📊 Round {round_num} complete: +{new_pages} pages, +{new_searches} searches"
        )

    # ========== Final Generation ==========
    print(f"\n{'=' * 50}")
    print(f"🧠 Final: Generating brand knowledge base")
    print(f"{'=' * 50}")

    all_pages = store.get_all_pages()
    all_searches = store.get_all_search_results()
    all_social = store.get_all_social()

    pages_for_structurer = [
        {"url": p["url"], "title": p["title"], "content": p["content"]}
        for p in all_pages
    ]
    search_for_structurer = []
    for s in all_searches:
        search_for_structurer.append(
            {
                "query": s.get("query", ""),
                "answer": s.get("answer", ""),
                "results": s.get("results", []),
                "source": s.get("source", ""),
            }
        )

    result = structure_brand(
        url, pages_for_structurer, clues, search_for_structurer, all_social
    )

    output_path = os.path.join(store.base_dir, "brand_knowledge.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n✅ Agent Pipeline complete in {elapsed:.1f}s")
    print(f"   Pages: {len(all_pages)}, Searches: {len(all_searches)}")

    return result
