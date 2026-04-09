"""AutoCrawl Engine — fully automatic brand knowledge base expansion.

Workflow:
1. Discover industries (LLM-generated or manual list)
2. For each industry, discover top brands (LLM-generated, deduped against DB)
3. Crawl brands one by one via the existing pipeline
4. Move to next industry, loop forever
"""

import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import SessionLocal, Brand, get_db
from admin import get_current_admin_user, batch_queue

MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
    "sk-cp-49r5TFMzeb7-z-HCbtIPK3h7NZPVs8QJIPVIBC9S3JDjeHq4pKU6YZ-srAyN1YH3-LR6wS0ot4f6xEcqR34SsBpE-yPuW-9kb_yGlDRaive4lhwduA3UAZs",
)

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "autocrawl_state.json")

# Default industry list (Chinese market focused)
DEFAULT_INDUSTRIES = [
    "科技互联网", "电商平台", "汽车", "金融保险", "医药健康",
    "教育培训", "餐饮连锁", "消费品", "美妆个护", "家电家居",
    "运动户外", "奢侈品时尚", "游戏娱乐", "旅游酒店", "房地产",
    "物流快递", "新能源", "人工智能", "半导体芯片", "文化传媒",
    "母婴用品", "宠物经济", "茶饮咖啡", "零食休闲", "服装鞋帽",
    "珠宝钟表", "家装建材", "农业食品", "工业制造", "通讯设备",
]

DEFAULT_CONFIG = {
    "daily_limit": 50,
    "concurrent": 3,
    "brands_per_industry": 30,
    "pause_between_brands_sec": 10,
    "industries": DEFAULT_INDUSTRIES,
}


class AutoCrawlEngine:
    """Background engine that automatically discovers and crawls brands."""

    def __init__(self):
        self.config = dict(DEFAULT_CONFIG)
        self.running = False
        self.paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Progress tracking
        self.current_industry = None
        self.current_industry_idx = 0
        self.current_brand = None
        self.today_count = 0
        self.today_date = None
        self.total_crawled = 0
        self.total_skipped = 0
        self.total_failed = 0
        self.industries_completed = []
        self.recent_log = []  # last 50 log entries

        # Per-industry progress: {industry: {total, done, failed, brands: [...]}}
        self.industry_progress = {}

        # Load persisted state
        self._load_state()

    def _log(self, msg: str):
        entry = {"time": datetime.now(timezone.utc).isoformat(), "msg": msg}
        self.recent_log.append(entry)
        if len(self.recent_log) > 100:
            self.recent_log = self.recent_log[-100:]
        print(f"🤖 AutoCrawl: {msg}")

    def _save_state(self):
        """Persist progress so we can resume after restart."""
        state = {
            "current_industry_idx": self.current_industry_idx,
            "total_crawled": self.total_crawled,
            "total_skipped": self.total_skipped,
            "total_failed": self.total_failed,
            "industries_completed": self.industries_completed,
            "industry_progress": self.industry_progress,
            "config": self.config,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.current_industry_idx = state.get("current_industry_idx", 0)
                self.total_crawled = state.get("total_crawled", 0)
                self.total_skipped = state.get("total_skipped", 0)
                self.total_failed = state.get("total_failed", 0)
                self.industries_completed = state.get("industries_completed", [])
                self.industry_progress = state.get("industry_progress", {})
                saved_config = state.get("config")
                if saved_config:
                    self.config.update(saved_config)
                self._log(f"Loaded state: {self.total_crawled} crawled, idx={self.current_industry_idx}")
            except Exception as e:
                self._log(f"Failed to load state: {e}")

    def _reset_daily_counter(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.today_date != today:
            self.today_date = today
            self.today_count = 0

    def _llm_call(self, prompt: str, max_tokens: int = 4000) -> str:
        resp = httpx.post(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.7",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        data = resp.json()
        if not data.get("choices"):
            raise ValueError(f"LLM error: {data.get('base_resp', {}).get('status_msg', 'unknown')}")
        return data["choices"][0]["message"]["content"]

    def _discover_brands(self, industry: str, count: int = 30) -> list:
        """Use LLM to discover top brands in an industry."""
        prompt = f"""列出"{industry}"行业的{count}个最知名品牌（优先中国市场的品牌，包括在中国运营的国际品牌），按知名度从高到低排序。

输出JSON数组，每个品牌格式：{{"name":"品牌名","url":"https://官网"}}

要求：
1. URL 必须是品牌真实官网（不是百度百科、维基等第三方页面）
2. 从行业龙头开始，逐步到中小品牌
3. 只输出JSON数组，不要其他文字"""

        content = self._llm_call(prompt)
        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        try:
            brands = json.loads(content.strip())
            return brands
        except json.JSONDecodeError:
            self._log(f"Failed to parse brand list for {industry}")
            return []

    def _get_existing_urls(self) -> set:
        db = SessionLocal()
        urls = set()
        for b in db.query(Brand).all():
            urls.add(b.url.rstrip("/"))
        db.close()
        return urls

    def _crawl_brand(self, name: str, url: str, category: str) -> str:
        """Submit a brand to the crawl pipeline via BatchQueue so it shows in Task Monitor."""
        from tasks import run_brand_pipeline

        db = SessionLocal()
        brand_id = str(uuid.uuid4())
        brand = Brand(id=brand_id, url=url, status="pending", category=category, name=name)
        db.add(brand)
        db.commit()
        db.close()

        # Register in BatchQueue for visibility in Task Monitor
        import threading as _threading
        t = _threading.Thread(target=run_brand_pipeline, args=(brand_id, url), daemon=True)
        t.start()

        now = datetime.now(timezone.utc).isoformat()
        batch_queue.total += 1
        with batch_queue._lock:
            batch_queue.running[brand_id] = {
                "thread": t, "name": name, "url": url,
                "started_at": now,
            }

        # Wait for completion (synchronous for autocrawl sequencing)
        t.join(timeout=600)  # 10 min max per brand

        # Clean up from BatchQueue running dict
        with batch_queue._lock:
            if brand_id in batch_queue.running:
                batch_queue.running.pop(brand_id)

        # Check result
        db = SessionLocal()
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        status = brand.status if brand else "unknown"
        if status == "done":
            batch_queue.completed.append(
                {"name": name, "url": url, "brand_id": brand_id,
                 "finished_at": datetime.now(timezone.utc).isoformat()}
            )
        elif status == "error":
            batch_queue.failed.append(
                {"name": name, "url": url, "brand_id": brand_id,
                 "error": brand.error_message if brand else "unknown"}
            )
        db.close()

        return status

    def start(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._log("Engine started")

    def stop(self):
        self.running = False
        self._stop_event.set()
        self._log("Engine stopping...")
        self._save_state()

    def pause(self):
        self.paused = True
        self._log("Engine paused")

    def resume(self):
        self.paused = False
        self._log("Engine resumed")

    def _run_loop(self):
        """Main loop: iterate industries → brands."""
        industries = self.config.get("industries", DEFAULT_INDUSTRIES)

        while self.running and not self._stop_event.is_set():
            # Reset daily counter
            self._reset_daily_counter()

            # Check daily limit
            if self.today_count >= self.config["daily_limit"]:
                self._log(f"Daily limit reached ({self.today_count}/{self.config['daily_limit']}). Sleeping until tomorrow...")
                # Sleep until midnight UTC
                now = datetime.now(timezone.utc)
                tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                sleep_secs = (tomorrow - now).total_seconds()
                self._stop_event.wait(min(sleep_secs, 3600))  # Check every hour
                continue

            # Pause check
            if self.paused:
                self._stop_event.wait(5)
                continue

            # Pick current industry
            if self.current_industry_idx >= len(industries):
                self._log("All industries completed! Restarting from the beginning with deeper crawl...")
                self.current_industry_idx = 0
                # Increase brands_per_industry for next round
                self.config["brands_per_industry"] = min(
                    self.config["brands_per_industry"] + 20, 100
                )
                self._save_state()

            industry = industries[self.current_industry_idx]
            self.current_industry = industry
            self._log(f"📂 Industry: {industry} (#{self.current_industry_idx + 1}/{len(industries)})")

            # Discover brands for this industry
            if industry not in self.industry_progress or not self.industry_progress[industry].get("brands"):
                self._log(f"🔍 Discovering brands for {industry}...")
                try:
                    discovered = self._discover_brands(industry, self.config["brands_per_industry"])
                    self.industry_progress[industry] = {
                        "total": len(discovered),
                        "done": 0,
                        "failed": 0,
                        "skipped": 0,
                        "brands": discovered,
                        "current_idx": 0,
                    }
                    self._log(f"Found {len(discovered)} brands for {industry}")
                    self._save_state()
                except Exception as e:
                    self._log(f"❌ Brand discovery failed for {industry}: {e}")
                    self.current_industry_idx += 1
                    self._save_state()
                    continue

            progress = self.industry_progress[industry]
            brands = progress.get("brands", [])
            current_idx = progress.get("current_idx", 0)

            if current_idx >= len(brands):
                # Industry done
                self._log(f"✅ Industry {industry} complete: {progress['done']} done, {progress['failed']} failed, {progress['skipped']} skipped")
                if industry not in self.industries_completed:
                    self.industries_completed.append(industry)
                self.current_industry_idx += 1
                self._save_state()
                continue

            # Get existing URLs to dedup
            existing_urls = self._get_existing_urls()

            # Process brands
            while current_idx < len(brands) and self.running and not self._stop_event.is_set():
                if self.paused:
                    self._stop_event.wait(5)
                    continue

                self._reset_daily_counter()
                if self.today_count >= self.config["daily_limit"]:
                    break

                brand_info = brands[current_idx]
                name = brand_info.get("name", "")
                url = brand_info.get("url", "")

                if not url or not url.startswith("http"):
                    progress["current_idx"] = current_idx + 1
                    progress["skipped"] += 1
                    current_idx += 1
                    continue

                # Dedup
                if url.rstrip("/") in existing_urls:
                    self._log(f"⏭️ Skip (exists): {name}")
                    progress["current_idx"] = current_idx + 1
                    progress["skipped"] += 1
                    self.total_skipped += 1
                    current_idx += 1
                    continue

                # Crawl
                self.current_brand = name
                self._log(f"🕷️ Crawling: {name} ({url})")

                try:
                    status = self._crawl_brand(name, url, industry)
                    if status == "done":
                        self._log(f"✅ Done: {name}")
                        progress["done"] += 1
                        self.total_crawled += 1
                    else:
                        self._log(f"⚠️ Status {status}: {name}")
                        progress["failed"] += 1
                        self.total_failed += 1
                except Exception as e:
                    self._log(f"❌ Failed: {name} — {str(e)[:100]}")
                    progress["failed"] += 1
                    self.total_failed += 1

                self.today_count += 1
                progress["current_idx"] = current_idx + 1
                current_idx += 1
                existing_urls.add(url.rstrip("/"))

                self._save_state()

                # Adaptive pause: slow down if we're hitting errors
                pause_sec = self.config.get("pause_between_brands_sec", 10)
                if status == "error":
                    # Back off more on errors (likely API overload)
                    pause_sec = max(pause_sec * 3, 30)
                    self._log(f"⏳ Error cooldown: waiting {pause_sec}s before next brand")
                if pause_sec > 0:
                    self._stop_event.wait(pause_sec)

            # If we exited because of daily limit, don't advance industry
            if current_idx >= len(brands):
                self.current_industry_idx += 1
                self._save_state()

        self.running = False
        self.current_brand = None
        self.current_industry = None
        self._log("Engine stopped")
        self._save_state()

    def status(self) -> dict:
        industries = self.config.get("industries", DEFAULT_INDUSTRIES)
        return {
            "running": self.running,
            "paused": self.paused,
            "current_industry": self.current_industry,
            "current_industry_idx": self.current_industry_idx,
            "total_industries": len(industries),
            "current_brand": self.current_brand,
            "today_count": self.today_count,
            "daily_limit": self.config["daily_limit"],
            "total_crawled": self.total_crawled,
            "total_skipped": self.total_skipped,
            "total_failed": self.total_failed,
            "industries_completed": self.industries_completed,
            "industry_progress": {
                k: {
                    "total": v.get("total", 0),
                    "done": v.get("done", 0),
                    "failed": v.get("failed", 0),
                    "skipped": v.get("skipped", 0),
                    "current_idx": v.get("current_idx", 0),
                }
                for k, v in self.industry_progress.items()
            },
            "config": self.config,
            "recent_log": self.recent_log[-30:],
        }


# Singleton
autocrawl_engine = AutoCrawlEngine()


# ============================================================
# API Router
# ============================================================

autocrawl_router = APIRouter(prefix="/api/admin/autocrawl", tags=["autocrawl"])


@autocrawl_router.get("/status")
def get_autocrawl_status(current_user=Depends(get_current_admin_user)):
    return autocrawl_engine.status()


@autocrawl_router.post("/start")
def start_autocrawl(current_user=Depends(get_current_admin_user)):
    autocrawl_engine.start()
    return {"message": "AutoCrawl started"}


@autocrawl_router.post("/stop")
def stop_autocrawl(current_user=Depends(get_current_admin_user)):
    autocrawl_engine.stop()
    return {"message": "AutoCrawl stopped"}


@autocrawl_router.post("/pause")
def pause_autocrawl(current_user=Depends(get_current_admin_user)):
    autocrawl_engine.pause()
    return {"message": "AutoCrawl paused"}


@autocrawl_router.post("/resume")
def resume_autocrawl(current_user=Depends(get_current_admin_user)):
    autocrawl_engine.resume()
    return {"message": "AutoCrawl resumed"}


class AutoCrawlConfig(BaseModel):
    daily_limit: Optional[int] = None
    concurrent: Optional[int] = None
    brands_per_industry: Optional[int] = None
    pause_between_brands_sec: Optional[int] = None
    industries: Optional[list[str]] = None


@autocrawl_router.put("/config")
def update_autocrawl_config(body: AutoCrawlConfig, current_user=Depends(get_current_admin_user)):
    if body.daily_limit is not None:
        autocrawl_engine.config["daily_limit"] = body.daily_limit
    if body.concurrent is not None:
        autocrawl_engine.config["concurrent"] = body.concurrent
    if body.brands_per_industry is not None:
        autocrawl_engine.config["brands_per_industry"] = body.brands_per_industry
    if body.pause_between_brands_sec is not None:
        autocrawl_engine.config["pause_between_brands_sec"] = body.pause_between_brands_sec
    if body.industries is not None:
        autocrawl_engine.config["industries"] = body.industries
    autocrawl_engine._save_state()
    return {"message": "Config updated", "config": autocrawl_engine.config}


@autocrawl_router.post("/reset")
def reset_autocrawl(current_user=Depends(get_current_admin_user)):
    """Reset all progress (start from scratch)."""
    autocrawl_engine.stop()
    autocrawl_engine.current_industry_idx = 0
    autocrawl_engine.total_crawled = 0
    autocrawl_engine.total_skipped = 0
    autocrawl_engine.total_failed = 0
    autocrawl_engine.industries_completed = []
    autocrawl_engine.industry_progress = {}
    autocrawl_engine.today_count = 0
    autocrawl_engine.recent_log = []
    autocrawl_engine._save_state()
    return {"message": "AutoCrawl progress reset"}


@autocrawl_router.post("/skip-industry")
def skip_industry(current_user=Depends(get_current_admin_user)):
    """Skip current industry and move to next."""
    autocrawl_engine.current_industry_idx += 1
    autocrawl_engine._save_state()
    return {"message": f"Skipped to industry #{autocrawl_engine.current_industry_idx}"}
