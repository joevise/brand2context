"""Background task runner for brand knowledge generation."""

import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from models import SessionLocal, Brand, generate_slug

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "brands")
os.makedirs(DATA_DIR, exist_ok=True)


def _fetch_logo(url: str) -> str:
    logo_url = None
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]

        import httpx

        clearbit_url = f"https://logo.clearbit.com/{domain}"
        resp = httpx.get(clearbit_url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            logo_url = clearbit_url
    except Exception:
        pass

    if not logo_url:
        try:
            import httpx

            resp = httpx.get(url, timeout=10.0, follow_redirects=True)
            html = resp.text

            og_image = re.search(
                r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
                html,
                re.I,
            )
            if og_image:
                logo_url = og_image.group(1)
            else:
                icons = re.findall(
                    r'<link[^>]*rel=["\'](?:icon|shortcut icon)["\'][^>]*href=["\']([^"\']+)["\']',
                    html,
                    re.I,
                )
                if icons:
                    icon_href = icons[0]
                    if icon_href.startswith("http"):
                        logo_url = icon_href
                    elif icon_href.startswith("//"):
                        logo_url = "https:" + icon_href
                    elif icon_href.startswith("/"):
                        logo_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}{icon_href}"
        except Exception:
            pass

    return logo_url


def _legacy_pipeline(brand_id: str, url: str, brand, db):
    """Legacy pipeline: crawl + search + structure (fallback when agent pipeline fails)."""
    from brand2context.crawler import crawl_site, crawl_site_incremental
    from brand2context.clue_extractor import extract_clues
    from brand2context.web_searcher import search_expand
    from brand2context.structurer import (
        structure_brand,
        structure_brand_incremental,
    )

    output_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    hashes_path = os.path.join(DATA_DIR, f"{brand_id}_hashes.json")

    previous_result = None
    previous_hashes = None
    is_incremental = False

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                previous_result = json.load(f)
            if previous_result and brand.status == "done":
                is_incremental = True
        except Exception:
            pass

    if is_incremental and os.path.exists(hashes_path):
        try:
            with open(hashes_path, "r", encoding="utf-8") as f:
                hashes_data = json.load(f)
                previous_hashes = hashes_data.get("hashes", {})
        except Exception:
            previous_hashes = None

    if is_incremental and previous_hashes is not None:
        print(f"🔄 增量更新模式: 检测到已有知识库")
        changed_pages, current_hashes, changed_urls = crawl_site_incremental(
            url, previous_hashes
        )

        if not changed_pages:
            print(f"📡 无页面变化，跳过爬取和 LLM 调用")
            brand.last_refreshed = datetime.now(timezone.utc)
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
            return None

        pages = changed_pages
        all_pages_for_context = pages
    else:
        if is_incremental:
            print(f"⚠️ 增量模式但无 hash 文件，将进行全量抓取")
        pages = crawl_site(url)

        if not pages:
            print(f"⚠️ 爬取失败，尝试 Metaso Reader: {url}")
            try:
                from brand2context.web_searcher import metaso_read_url

                content = metaso_read_url(url)
                if content and len(content) > 100:
                    pages = [{"url": url, "content": content}]
                    print(f"   ✅ Metaso Reader 成功，获取 {len(content)} 字符")
                else:
                    print(f"   ⚠️ Metaso Reader 内容太少，跳过")
            except Exception as e:
                print(f"   ⚠️ Metaso Reader 失败: {e}")

    clues = extract_clues(pages, url)

    if not pages:
        print(f"⚠️ 爬取失败，启用搜索降级模式: {url}")
        if not clues.get("brand_name"):
            brand_name_guess = brand.name
            if not brand_name_guess:
                domain = urlparse(url).netloc.replace("www.", "").split(".")[0]
                brand_name_guess = domain.capitalize()
            clues["brand_name"] = brand_name_guess
            clues["url"] = url
            print(f"   → 推测品牌名: {brand_name_guess}")

    brand.progress_step = "searching"
    db.commit()

    search_results = search_expand(clues, pages=pages)

    if not pages and not search_results:
        print(f"⚠️ 常规搜索也失败，尝试扩展搜索...")
        brand_name = clues.get("brand_name", "")
        if brand_name:
            try:
                import requests as req
                from brand2context.config import TAVILY_API_KEY, TAVILY_ENDPOINT

                if TAVILY_API_KEY:
                    for q in [f"{brand_name} 品牌 官网", f"{brand_name} brand"]:
                        resp = req.post(
                            TAVILY_ENDPOINT,
                            json={
                                "query": q,
                                "max_results": 8,
                                "include_answer": True,
                            },
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {TAVILY_API_KEY}",
                            },
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            search_results.append(
                                {
                                    "query": q,
                                    "answer": data.get("answer", ""),
                                    "results": [
                                        {
                                            "title": r.get("title", ""),
                                            "url": r.get("url", ""),
                                            "content": r.get("content", ""),
                                        }
                                        for r in data.get("results", [])
                                    ],
                                }
                            )
                            print(
                                f"   ✅ 扩展搜索 '{q}' → {len(data.get('results', []))} results"
                            )
            except Exception as e:
                print(f"   ⚠️ 扩展搜索失败: {e}")

    social_results = []
    brand_name_for_social = clues.get("brand_name", "")
    if brand_name_for_social:
        try:
            import httpx

            social_api_url = os.getenv(
                "SOCIAL_API_URL", "http://host.docker.internal:8006"
            )
            resp = httpx.post(
                f"{social_api_url}/api/social/crawl/{brand_name_for_social}",
                timeout=300,
            )
            if resp.status_code == 200:
                data = resp.json()
                social_results = data.get("results", [])
                print(f"📱 社交媒体抓取完成，获得 {len(social_results)} 条数据")
            else:
                print(f"⚠️ 社交媒体 API 返回 {resp.status_code}")
        except Exception as e:
            print(f"⚠️ 社交媒体抓取跳过: {e}")

    if not pages and not search_results:
        brand.status = "error"
        brand.progress_step = "error"
        brand.error_message = (
            "No data collected from URL and search fallback also failed"
        )
        brand.updated_at = datetime.now(timezone.utc)
        db.commit()
        return None

    if not pages and search_results:
        print(f"📡 降级模式：使用搜索结果生成知识库（无官网爬取数据）")

    brand.progress_step = "structuring"
    db.commit()

    if is_incremental and previous_result and changed_pages:
        result = structure_brand_incremental(
            url,
            changed_pages,
            all_pages_for_context,
            clues,
            search_results,
            social_results,
            previous_result,
            changed_urls,
        )
    else:
        result = structure_brand(url, pages, clues, search_results, social_results)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if is_incremental and "current_hashes" in dir():
        hashes_data = {
            "hashes": current_hashes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(hashes_path, "w", encoding="utf-8") as f:
            json.dump(hashes_data, f, ensure_ascii=False, indent=2)

    return result


def run_brand_pipeline(brand_id: str, url: str):
    """Run the brand2context pipeline for a given URL."""
    db = SessionLocal()
    try:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            return
        brand.status = "processing"
        brand.progress_step = "crawling"
        brand.updated_at = datetime.now(timezone.utc)
        db.commit()

        from brand2context.agent_pipeline import run_agent_pipeline

        try:
            result = run_agent_pipeline(
                brand_id=brand_id,
                url=url,
                brand_name=brand.name or "",
                category=brand.category or "",
                data_dir=DATA_DIR,
            )
        except Exception as e:
            print(f"⚠️ Agent pipeline failed: {e}, falling back to legacy pipeline")
            result = _legacy_pipeline(brand_id, url, brand, db)
            if result is None:
                return

        brand_name = result.get("identity", {}).get("name", "Unknown Brand")
        brand.name = brand_name
        brand.slug = generate_slug(brand_name, db)
        brand.description = result.get("identity", {}).get("tagline", "") or result.get(
            "identity", {}
        ).get("positioning", "")
        brand.status = "done"
        brand.progress_step = "done"
        brand.updated_at = datetime.now(timezone.utc)
        brand.last_refreshed = datetime.now(timezone.utc)
        db.commit()

        logo_url = _fetch_logo(url)
        if logo_url:
            brand.logo_url = logo_url
            db.commit()

        try:
            from vector import index_brand

            index_brand(brand_id, result)
        except Exception as e:
            print(f"Warning: ChromaDB indexing failed: {e}")

    except Exception as e:
        traceback.print_exc()
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            brand.status = "error"
            brand.progress_step = "error"
            brand.error_message = str(e)[:500]
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
