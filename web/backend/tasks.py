"""Background task runner for brand knowledge generation."""

import json
import os
import sys
import traceback
from datetime import datetime, timezone

# Add parent directories to path so we can import brand2context
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from models import SessionLocal, Brand

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "brands")
os.makedirs(DATA_DIR, exist_ok=True)


def run_brand_pipeline(brand_id: str, url: str):
    """Run the brand2context pipeline for a given URL."""
    db = SessionLocal()
    try:
        # Update status to processing
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            return
        brand.status = "processing"
        brand.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Import and run pipeline
        from brand2context.crawler import crawl_site
        from brand2context.clue_extractor import extract_clues
        from brand2context.web_searcher import search_expand
        from brand2context.structurer import structure_brand

        # Step 1: Crawl
        pages = crawl_site(url)

        # Step 2: Extract clues
        clues = extract_clues(pages, url)

        # Step 3: Web search expansion
        search_results = search_expand(clues)

        # Step 3.5: Social media crawl (通过 HTTP 调用容器外的 social API)
        social_results = []
        brand_name_for_social = clues.get("brand_name", "")
        if brand_name_for_social:
            try:
                import httpx
                social_api_url = os.getenv("SOCIAL_API_URL", "http://host.docker.internal:8006")
                resp = httpx.post(f"{social_api_url}/api/social/crawl/{brand_name_for_social}", timeout=300)
                if resp.status_code == 200:
                    data = resp.json()
                    social_results = data.get("results", [])
                    print(f"📱 社交媒体抓取完成，获得 {len(social_results)} 条数据")
                else:
                    print(f"⚠️ 社交媒体 API 返回 {resp.status_code}")
            except Exception as e:
                print(f"⚠️ 社交媒体抓取跳过: {e}")

        # Step 4: Structure
        if not pages and not search_results:
            brand.status = "error"
            brand.error_message = "No data collected from URL"
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
            return

        result = structure_brand(url, pages, clues, search_results, social_results)

        # Save JSON
        output_path = os.path.join(DATA_DIR, f"{brand_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Update brand record
        brand_name = result.get("identity", {}).get("name", "Unknown Brand")
        brand.name = brand_name
        brand.status = "done"
        brand.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Index in ChromaDB
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
            brand.error_message = str(e)[:500]
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
