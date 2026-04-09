"""Admin API for Brand2Context — seed management, batch crawling, refresh scheduling."""

import json
import os
import uuid
import queue
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import SessionLocal, Brand, ApiCallLog, User, get_db, generate_slug
from tasks import run_brand_pipeline

JWT_SECRET = os.getenv("JWT_SECRET", "brand2context-dev-secret")

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_current_admin_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


SEEDS_FILE = os.path.join(os.path.dirname(__file__), "seeds", "brands_seed.json")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "seeds", "settings.json")
# LLM config
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from brand2context.config import LLM_API_KEY, LLM_MODEL, LLM_ENDPOINT

# ============================================================
# Settings
# ============================================================

DEFAULT_SETTINGS = {"refresh_cycle_days": 30, "max_concurrent": 5}


def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    return dict(DEFAULT_SETTINGS)


def _save_settings(s):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


@admin_router.get("/settings")
def get_settings(current_user: User = Depends(get_current_admin_user)):
    return _load_settings()


class SettingsUpdate(BaseModel):
    refresh_cycle_days: Optional[int] = None
    max_concurrent: Optional[int] = None


@admin_router.put("/settings")
def update_settings(
    body: SettingsUpdate, current_user: User = Depends(get_current_admin_user)
):
    s = _load_settings()
    if body.refresh_cycle_days is not None:
        s["refresh_cycle_days"] = body.refresh_cycle_days
    if body.max_concurrent is not None:
        s["max_concurrent"] = body.max_concurrent
        batch_queue.max_concurrent = body.max_concurrent
    _save_settings(s)
    return s


# ============================================================
# Seed Library
# ============================================================


def _load_seeds():
    if os.path.exists(SEEDS_FILE):
        with open(SEEDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_seeds(seeds):
    os.makedirs(os.path.dirname(SEEDS_FILE), exist_ok=True)
    with open(SEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)


@admin_router.get("/seeds")
def list_seeds(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    seeds = _load_seeds()
    if category:
        seeds = [s for s in seeds if s.get("category") == category]

    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    # Match seeds against DB
    all_brands = db.query(Brand).all()
    url_map = {}
    for b in all_brands:
        url_map[b.url.rstrip("/")] = b

    result = []
    for s in seeds:
        url = s.get("url", "").rstrip("/")
        brand = url_map.get(url)
        entry = {
            "name": s.get("name", ""),
            "url": s.get("url", ""),
            "category": s.get("category", ""),
        }
        if brand:
            entry["brand_id"] = brand.id
            entry["status"] = brand.status
            entry["last_refreshed"] = (
                brand.last_refreshed.isoformat() if brand.last_refreshed else None
            )
            if (
                brand.status == "done"
                and brand.last_refreshed
                and brand.last_refreshed.replace(tzinfo=timezone.utc) < cutoff
            ):
                entry["status"] = "outdated"
        else:
            entry["status"] = "new"
            entry["brand_id"] = None
            entry["last_refreshed"] = None
        result.append(entry)

    # Categories summary
    cats = {}
    for s in _load_seeds():
        c = s.get("category", "未分类")
        cats[c] = cats.get(c, 0) + 1

    return {
        "seeds": result,
        "total": len(result),
        "categories": [
            {"name": k, "count": v}
            for k, v in sorted(cats.items(), key=lambda x: -x[1])
        ],
    }


class SeedCreate(BaseModel):
    name: str
    url: str
    category: str = ""


@admin_router.post("/seeds")
def add_seed(body: SeedCreate, current_user: User = Depends(get_current_admin_user)):
    seeds = _load_seeds()
    url = body.url.rstrip("/")
    if any(s.get("url", "").rstrip("/") == url for s in seeds):
        return {"message": "Already exists", "added": False}
    seeds.append({"name": body.name, "url": body.url, "category": body.category})
    _save_seeds(seeds)
    return {"message": "Added", "added": True, "total": len(seeds)}


class AIGenerateRequest(BaseModel):
    category: str
    count: int = 20


@admin_router.post("/seeds/ai-generate")
def ai_generate_seeds(
    body: AIGenerateRequest, current_user: User = Depends(get_current_admin_user)
):
    prompt = f"""列出"{body.category}"品类的{body.count}个知名品牌（中国品牌和在中国运营的国际品牌），JSON数组格式。
    每个品牌格式：{{"name":"品牌名","url":"https://官网","category":"{body.category}"}}
    要求：URL 必须是真实可访问的官网。只输出json数组，不要其他文字。"""

    try:
        resp = httpx.post(
            LLM_ENDPOINT,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        content = resp.json()["choices"][0]["message"]["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        new_brands = json.loads(content.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    seeds = _load_seeds()
    existing_urls = {s.get("url", "").rstrip("/") for s in seeds}
    added = []
    for b in new_brands:
        url = b.get("url", "").rstrip("/")
        if url and url not in existing_urls:
            entry = {
                "name": b.get("name", ""),
                "url": b.get("url", ""),
                "category": body.category,
            }
            seeds.append(entry)
            added.append(entry)
            existing_urls.add(url)
    _save_seeds(seeds)
    return {"added": len(added), "brands": added, "total_seeds": len(seeds)}


class SearchAddRequest(BaseModel):
    brand_name: str
    category: str = ""


@admin_router.post("/seeds/search-add")
def search_add_seed(
    body: SearchAddRequest, current_user: User = Depends(get_current_admin_user)
):
    prompt = f"""找到"{body.brand_name}"这个品牌的官方网站URL。
    只返回JSON：{{"name":"品牌名","url":"https://官网"}}
    不要其他文字。"""

    try:
        resp = httpx.post(
            LLM_ENDPOINT,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=30.0,
        )
        content = resp.json()["choices"][0]["message"]["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    seeds = _load_seeds()
    url = result.get("url", "").rstrip("/")
    if any(s.get("url", "").rstrip("/") == url for s in seeds):
        return {"message": "Already exists", "added": False, "brand": result}

    entry = {
        "name": result.get("name", body.brand_name),
        "url": result.get("url", ""),
        "category": body.category,
    }
    seeds.append(entry)
    _save_seeds(seeds)
    return {"message": "Added", "added": True, "brand": entry}


# ============================================================
# Batch Queue
# ============================================================


class BatchQueue:
    def __init__(self, max_concurrent=5):
        self.q = queue.Queue()
        self.max_concurrent = max_concurrent
        self.running = {}
        self.completed = []
        self.failed = []
        self.cancelled = []
        self.paused = False
        self.task_id = None
        self.total = 0
        self.started_at = None
        self._lock = threading.Lock()
        self._worker_thread = None

    def start(self, brands_to_crawl):
        self.task_id = str(uuid.uuid4())[:8]
        self.completed = []
        self.failed = []
        self.cancelled = []
        self.running = {}
        self.paused = False
        self.total = len(brands_to_crawl)
        self.started_at = datetime.now(timezone.utc).isoformat()

        for b in brands_to_crawl:
            self.q.put(b)

        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

        return self.task_id

    def _worker(self):
        while True:
            if self.q.empty() and not self.running:
                break

            if self.paused:
                time.sleep(1)
                continue

            # Clean finished threads
            with self._lock:
                done_ids = [
                    bid
                    for bid, info in self.running.items()
                    if not info["thread"].is_alive()
                ]
                for bid in done_ids:
                    info = self.running.pop(bid)
                    # Check DB for result
                    db = SessionLocal()
                    brand = db.query(Brand).filter(Brand.id == bid).first()
                    if brand and brand.status == "done":
                        self.completed.append(
                            {"name": info["name"], "url": info["url"], "brand_id": bid,
                             "finished_at": datetime.now(timezone.utc).isoformat()}
                        )
                    elif brand and brand.status == "error":
                        error_msg = brand.error_message or ""
                        if "Cancelled" in error_msg:
                            self.cancelled.append(
                                {"name": info["name"], "url": info["url"], "brand_id": bid}
                            )
                        else:
                            self.failed.append(
                                {
                                    "name": info["name"],
                                    "url": info["url"],
                                    "brand_id": bid,
                                    "error": brand.error_message,
                                }
                            )
                    else:
                        self.completed.append(
                            {"name": info["name"], "url": info["url"], "brand_id": bid,
                             "finished_at": datetime.now(timezone.utc).isoformat()}
                        )
                    db.close()

            # Start new tasks if capacity available
            while (
                len(self.running) < self.max_concurrent
                and not self.q.empty()
                and not self.paused
            ):
                item = self.q.get()
                url = item.get("url", "")
                name = item.get("name", "")
                category = item.get("category", "")

                if not url.startswith("http"):
                    url = "https://" + url

                # Reuse existing brand_id if provided (e.g. from refresh/retry)
                brand_id = item.get("brand_id")
                if brand_id:
                    db = SessionLocal()
                    brand = db.query(Brand).filter(Brand.id == brand_id).first()
                    if brand:
                        brand.status = "processing"
                        brand.progress_step = "crawling"
                        brand.error_message = None
                        brand.updated_at = datetime.now(timezone.utc)
                        db.commit()
                    db.close()
                else:
                    brand_id = str(uuid.uuid4())
                    db = SessionLocal()
                    brand = Brand(id=brand_id, url=url, status="pending", category=category)
                    db.add(brand)
                    db.commit()
                    db.close()

                t = threading.Thread(
                    target=run_brand_pipeline, args=(brand_id, url), daemon=True
                )
                t.start()

                now = datetime.now(timezone.utc).isoformat()
                with self._lock:
                    self.running[brand_id] = {
                        "thread": t, "name": name, "url": url,
                        "started_at": now,
                    }

            time.sleep(2)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def cancel_brand(self, brand_id: str):
        """Cancel a single running or queued brand task."""
        db = SessionLocal()
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand and brand.status in ("processing", "pending"):
            brand.status = "error"
            brand.progress_step = "error"
            brand.error_message = "Cancelled by user"
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
        db.close()
        # Remove from running dict (thread will finish on its own but brand is marked)
        with self._lock:
            if brand_id in self.running:
                info = self.running.pop(brand_id)
                self.cancelled.append(
                    {"name": info["name"], "url": info["url"], "brand_id": brand_id}
                )

    def cancel_all_queued(self):
        """Cancel all queued (not yet running) tasks."""
        cancelled_count = 0
        while not self.q.empty():
            try:
                item = self.q.get_nowait()
                cancelled_count += 1
                self.cancelled.append(
                    {"name": item.get("name", ""), "url": item.get("url", "")}
                )
            except queue.Empty:
                break
        self.total -= cancelled_count
        return cancelled_count

    def ensure_worker(self):
        """Make sure a worker thread is running to consume the queue."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def status(self):
        with self._lock:
            running_list = []
            for k, v in self.running.items():
                item = {
                    "name": v["name"], "url": v["url"], "brand_id": k,
                    "started_at": v.get("started_at"),
                }
                running_list.append(item)

        # Enrich running items with progress_step from DB
        if running_list:
            db = SessionLocal()
            for item in running_list:
                brand = db.query(Brand).filter(Brand.id == item["brand_id"]).first()
                if brand:
                    item["progress_step"] = brand.progress_step or "pending"
                    item["name"] = brand.name or item["name"]
                else:
                    item["progress_step"] = "unknown"
            db.close()

        return {
            "task_id": self.task_id,
            "total": self.total,
            "completed": len(self.completed),
            "processing": len(running_list),
            "queued": self.q.qsize(),
            "failed": len(self.failed),
            "cancelled": len(self.cancelled),
            "paused": self.paused,
            "started_at": self.started_at,
            "running_items": running_list,
            "completed_items": self.completed[-50:],
            "failed_items": self.failed,
            "cancelled_items": self.cancelled[-20:],
        }

    def retry_failed(self):
        items = list(self.failed)
        self.failed = []
        for item in items:
            self.q.put({"name": item["name"], "url": item["url"], "category": ""})
        self.total += len(items)
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
        return len(items)


batch_queue = BatchQueue()


# ============================================================
# Batch API
# ============================================================


class BatchStartRequest(BaseModel):
    category: Optional[str] = None
    batch_size: int = 10
    filter: str = "new"  # "new", "outdated", "all"


@admin_router.post("/batch/start")
def start_batch(
    body: BatchStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    seeds = _load_seeds()
    if body.category:
        seeds = [s for s in seeds if s.get("category") == body.category]

    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    all_brands = db.query(Brand).all()
    url_map = {b.url.rstrip("/"): b for b in all_brands}

    to_crawl = []
    for s in seeds:
        url = s.get("url", "").rstrip("/")
        brand = url_map.get(url)

        if body.filter == "new" and brand is not None:
            continue
        if body.filter == "outdated":
            if not brand or brand.status != "done":
                continue
            if (
                brand.last_refreshed
                and brand.last_refreshed.replace(tzinfo=timezone.utc) >= cutoff
            ):
                continue
        # "all" — include everything not currently processing
        if brand and brand.status == "processing":
            continue

        to_crawl.append(s)

        if len(to_crawl) >= body.batch_size:
            break

    if not to_crawl:
        return {"task_id": None, "total": 0, "message": "No brands to crawl"}

    batch_queue.max_concurrent = settings["max_concurrent"]
    task_id = batch_queue.start(to_crawl)
    return {
        "task_id": task_id,
        "total": len(to_crawl),
        "message": f"Started {len(to_crawl)} brands",
    }


@admin_router.get("/batch/status")
def get_batch_status(current_user: User = Depends(get_current_admin_user)):
    return batch_queue.status()


@admin_router.post("/batch/pause")
def pause_batch(current_user: User = Depends(get_current_admin_user)):
    batch_queue.pause()
    return {"message": "Paused", "paused": True}


@admin_router.post("/batch/resume")
def resume_batch(current_user: User = Depends(get_current_admin_user)):
    batch_queue.resume()
    return {"message": "Resumed", "paused": False}


@admin_router.post("/batch/retry-failed")
def retry_failed(current_user: User = Depends(get_current_admin_user)):
    count = batch_queue.retry_failed()
    return {"message": f"Retrying {count} failed brands", "count": count}


@admin_router.post("/batch/cancel/{brand_id}")
def cancel_brand_task(
    brand_id: str, current_user: User = Depends(get_current_admin_user)
):
    batch_queue.cancel_brand(brand_id)
    return {"message": f"Cancelled brand {brand_id}"}


@admin_router.post("/batch/cancel-all")
def cancel_all_tasks(current_user: User = Depends(get_current_admin_user)):
    count = batch_queue.cancel_all_queued()
    return {"message": f"Cancelled {count} queued tasks", "count": count}


@admin_router.post("/batch/reset-stuck")
def reset_stuck_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Reset all stuck processing/pending brands to error, and clear the batch queue."""
    stuck = db.query(Brand).filter(Brand.status.in_(["processing", "pending"])).all()
    for b in stuck:
        b.status = "error"
        b.progress_step = "error"
        b.error_message = "Manual reset: cleared stuck task"
        b.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Also drain the in-memory queue
    drained = 0
    while not batch_queue.q.empty():
        try:
            batch_queue.q.get_nowait()
            drained += 1
        except queue.Empty:
            break

    # Reset batch queue state
    with batch_queue._lock:
        batch_queue.running.clear()
    batch_queue.total = 0

    return {
        "message": f"Reset {len(stuck)} stuck brands and drained {drained} queued items",
        "stuck_reset": len(stuck),
        "queue_drained": drained,
    }


class RetryDBRequest(BaseModel):
    batch_size: int = 10


@admin_router.post("/batch/retry-db-errors")
def retry_db_errors(
    body: RetryDBRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Retry all brands with status='error' in the database."""
    error_brands = (
        db.query(Brand)
        .filter(Brand.status == "error")
        .order_by(Brand.created_at.desc())
        .limit(body.batch_size)
        .all()
    )

    if not error_brands:
        return {"message": "No error brands to retry", "count": 0}

    # Reset their status and re-queue
    to_crawl = []
    for b in error_brands:
        b.status = "pending"
        b.error_message = None
        b.updated_at = datetime.now(timezone.utc)
        to_crawl.append(
            {
                "name": b.name or "",
                "url": b.url,
                "category": b.category or "",
                "brand_id": b.id,
            }
        )
    db.commit()

    # Use existing brand IDs instead of creating new ones
    settings = _load_settings()
    batch_queue.max_concurrent = settings["max_concurrent"]

    # Custom start that reuses existing brand records
    batch_queue.task_id = str(uuid.uuid4())[:8]
    batch_queue.completed = []
    batch_queue.failed = []
    batch_queue.running = {}
    batch_queue.paused = False
    batch_queue.total = len(to_crawl)

    for item in to_crawl:
        batch_queue.q.put(item)

    if batch_queue._worker_thread is None or not batch_queue._worker_thread.is_alive():
        batch_queue._worker_thread = threading.Thread(target=_retry_worker, daemon=True)
        batch_queue._worker_thread.start()

    return {"message": f"Retrying {len(to_crawl)} error brands", "count": len(to_crawl)}


def _retry_worker():
    """Worker that reuses existing brand IDs for retry."""
    while True:
        if batch_queue.q.empty() and not batch_queue.running:
            break
        if batch_queue.paused:
            time.sleep(1)
            continue

        # Clean finished threads
        with batch_queue._lock:
            done_ids = [
                bid
                for bid, info in batch_queue.running.items()
                if not info["thread"].is_alive()
            ]
            for bid in done_ids:
                info = batch_queue.running.pop(bid)
                db = SessionLocal()
                brand = db.query(Brand).filter(Brand.id == bid).first()
                if brand and brand.status == "done":
                    batch_queue.completed.append(
                        {"name": info["name"], "url": info["url"], "brand_id": bid}
                    )
                elif brand and brand.status == "error":
                    batch_queue.failed.append(
                        {
                            "name": info["name"],
                            "url": info["url"],
                            "brand_id": bid,
                            "error": brand.error_message,
                        }
                    )
                else:
                    batch_queue.completed.append(
                        {"name": info["name"], "url": info["url"], "brand_id": bid}
                    )
                db.close()

        while (
            len(batch_queue.running) < batch_queue.max_concurrent
            and not batch_queue.q.empty()
            and not batch_queue.paused
        ):
            item = batch_queue.q.get()
            url = item.get("url", "")
            name = item.get("name", "")
            brand_id = item.get("brand_id")

            if not url.startswith("http"):
                url = "https://" + url

            # Reuse existing brand_id if provided, otherwise create new
            if not brand_id:
                brand_id = str(uuid.uuid4())
                db = SessionLocal()
                brand = Brand(
                    id=brand_id,
                    url=url,
                    status="pending",
                    category=item.get("category", ""),
                )
                db.add(brand)
                db.commit()
                db.close()

            t = threading.Thread(
                target=run_brand_pipeline, args=(brand_id, url), daemon=True
            )
            t.start()

            with batch_queue._lock:
                batch_queue.running[brand_id] = {"thread": t, "name": name, "url": url}

        time.sleep(2)


# ============================================================
# Refresh Scheduling
# ============================================================


@admin_router.get("/refresh-status")
def get_refresh_status(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)
):
    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    done_brands = (
        db.query(Brand).filter(Brand.status == "done", Brand.is_public == True).all()
    )

    up_to_date = 0
    outdated = []
    for b in done_brands:
        if b.last_refreshed and b.last_refreshed.replace(tzinfo=timezone.utc) >= cutoff:
            up_to_date += 1
        else:
            days_since = (
                (
                    datetime.now(timezone.utc)
                    - (
                        b.last_refreshed.replace(tzinfo=timezone.utc)
                        if b.last_refreshed
                        else b.created_at.replace(tzinfo=timezone.utc)
                    )
                ).days
                if (b.last_refreshed or b.created_at)
                else 999
            )
            outdated.append(
                {
                    "id": b.id,
                    "name": b.name,
                    "url": b.url,
                    "last_refreshed": b.last_refreshed.isoformat()
                    if b.last_refreshed
                    else None,
                    "days_since": days_since,
                }
            )

    return {
        "total_brands": len(done_brands),
        "up_to_date": up_to_date,
        "outdated": len(outdated),
        "outdated_brands": sorted(outdated, key=lambda x: -x["days_since"]),
        "refresh_cycle_days": cycle_days,
    }


class RefreshRequest(BaseModel):
    batch_size: int = 10


@admin_router.post("/refresh-outdated")
def refresh_outdated(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    outdated = (
        db.query(Brand)
        .filter(
            Brand.status == "done",
            Brand.is_public == True,
        )
        .all()
    )

    to_refresh = []
    for b in outdated:
        if (
            not b.last_refreshed
            or b.last_refreshed.replace(tzinfo=timezone.utc) < cutoff
        ):
            to_refresh.append(
                {"name": b.name or "", "url": b.url, "category": b.category or ""}
            )
        if len(to_refresh) >= body.batch_size:
            break

    if not to_refresh:
        return {"message": "No outdated brands", "total": 0}

    batch_queue.max_concurrent = settings["max_concurrent"]
    task_id = batch_queue.start(to_refresh)
    return {
        "task_id": task_id,
        "total": len(to_refresh),
        "message": f"Refreshing {len(to_refresh)} brands",
    }


# ============================================================
# Dashboard
# ============================================================


@admin_router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)
):
    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    total_brands = db.query(Brand).filter(Brand.status == "done").count()

    by_category = (
        db.query(Brand.category, func.count(Brand.id))
        .filter(Brand.status == "done", Brand.category.isnot(None))
        .group_by(Brand.category)
        .all()
    )

    by_status = {}
    for status in ["done", "processing", "error", "pending"]:
        by_status[status] = db.query(Brand).filter(Brand.status == status).count()

    recent = db.query(Brand).order_by(Brand.created_at.desc()).limit(10).all()

    failed = (
        db.query(Brand)
        .filter(Brand.status == "error")
        .order_by(Brand.created_at.desc())
        .limit(10)
        .all()
    )

    outdated_count = 0
    for b in db.query(Brand).filter(Brand.status == "done").all():
        if (
            not b.last_refreshed
            or b.last_refreshed.replace(tzinfo=timezone.utc) < cutoff
        ):
            outdated_count += 1

    total_api_calls = db.query(func.sum(ApiCallLog.call_count)).scalar() or 0

    queue_status = batch_queue.status()

    return {
        "total_brands": total_brands,
        "brands_by_category": [
            {"name": name, "count": count} for name, count in by_category
        ],
        "brands_by_status": by_status,
        "recent_brands": [
            {
                "name": b.name,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "status": b.status,
            }
            for b in recent
        ],
        "failed_brands": [
            {
                "name": b.name,
                "error_message": b.error_message,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in failed
        ],
        "outdated_count": outdated_count,
        "queue_status": {
            "running": queue_status["processing"],
            "queued": queue_status["queued"],
            "paused": queue_status["paused"],
        },
        "total_api_calls": total_api_calls,
    }


# ============================================================
# Industry Management
# ============================================================


class IndustryLaunchRequest(BaseModel):
    industry: str
    count: int = 30


@admin_router.post("/industry/launch")
def launch_industry(
    body: IndustryLaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    prompt = f"""列出"{body.industry}"行业的{body.count}个知名品牌（中国品牌和在中国运营的国际品牌），JSON数组格式。
    每个品牌格式：{{"name":"品牌名","url":"https://官网","category":"{body.industry}"}}
    要求：URL 必须是真实可访问的官网。只输出json数组，不要其他文字。"""

    try:
        resp = httpx.post(
            LLM_ENDPOINT,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        content = resp.json()["choices"][0]["message"]["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        new_brands = json.loads(content.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    seeds = _load_seeds()
    existing_urls = {s.get("url", "").rstrip("/") for s in seeds}

    db_brands = db.query(Brand).all()
    db_urls = {b.url.rstrip("/"): b for b in db_brands}
    existing_urls.update(db_urls.keys())

    for b in db_brands:
        url = b.url.rstrip("/")
        if url not in existing_urls:
            entry = {
                "name": b.name or "",
                "url": b.url,
                "category": b.category or body.industry,
            }
            seeds.append(entry)
            existing_urls.add(url)
    _save_seeds(seeds)

    added = []
    for b in new_brands:
        url = b.get("url", "").rstrip("/")
        if url and url not in existing_urls:
            entry = {
                "name": b.get("name", ""),
                "url": b.get("url", ""),
                "category": body.industry,
            }
            seeds.append(entry)
            added.append(entry)
            existing_urls.add(url)
    _save_seeds(seeds)

    db_brands = db.query(Brand).all()
    db_urls = {b.url.rstrip("/"): b for b in db_brands}

    to_crawl = []
    for entry in added:
        url = entry.get("url", "").rstrip("/")
        brand = db_urls.get(url)
        if brand is None:
            to_crawl.append(entry)
        elif brand.status == "error":
            brand.status = "pending"
            brand.error_message = None
            brand.updated_at = datetime.now(timezone.utc)
            to_crawl.append(
                {
                    "name": entry["name"],
                    "url": entry["url"],
                    "category": body.industry,
                    "brand_id": brand.id,
                }
            )
            db_urls[url] = "pending"
        db.commit()

    if not to_crawl:
        return {
            "task_id": None,
            "industry": body.industry,
            "brands_added": len(added),
            "brands_started": 0,
            "message": "All brands already exist in database",
        }

    settings = _load_settings()
    batch_queue.max_concurrent = settings["max_concurrent"]
    task_id = batch_queue.start(to_crawl)

    return {
        "task_id": task_id,
        "industry": body.industry,
        "brands_added": len(added),
        "brands_started": len(to_crawl),
    }


@admin_router.get("/industry/stats")
def get_industry_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)
):
    brands = db.query(Brand).all()
    cats = {}
    for b in brands:
        cat = b.category or "未分类"
        if cat not in cats:
            cats[cat] = {
                "total": 0,
                "done": 0,
                "processing": 0,
                "error": 0,
                "pending": 0,
                "last_updated": None,
            }
        cats[cat]["total"] += 1
        cats[cat][b.status] = cats[cat].get(b.status, 0) + 1
        if b.updated_at and (
            cats[cat]["last_updated"] is None
            or b.updated_at > cats[cat]["last_updated"]
        ):
            cats[cat]["last_updated"] = b.updated_at

    stats = []
    for cat_name, cat_data in cats.items():
        total = cat_data["total"]
        done = cat_data["done"]
        completion_rate = done / total if total > 0 else 0
        stats.append(
            {
                "name": cat_name,
                "total": total,
                "done": done,
                "processing": cat_data["processing"],
                "error": cat_data["error"],
                "pending": cat_data["pending"],
                "completion_rate": round(completion_rate, 2),
                "last_updated": cat_data["last_updated"].isoformat()
                if cat_data["last_updated"]
                else None,
            }
        )

    stats.sort(key=lambda x: -x["completion_rate"])
    return {"industries": stats}


class IndustryRetryRequest(BaseModel):
    industry: str


@admin_router.post("/industry/retry")
def retry_industry(
    body: IndustryRetryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    error_brands = (
        db.query(Brand)
        .filter(Brand.status == "error", Brand.category == body.industry)
        .all()
    )

    if not error_brands:
        return {"message": "No error brands to retry", "count": 0}

    to_crawl = []
    for b in error_brands:
        b.status = "pending"
        b.error_message = None
        b.updated_at = datetime.now(timezone.utc)
        to_crawl.append(
            {
                "name": b.name or "",
                "url": b.url,
                "category": b.category or "",
                "brand_id": b.id,
            }
        )
    db.commit()

    settings = _load_settings()
    batch_queue.max_concurrent = settings["max_concurrent"]

    batch_queue.task_id = str(uuid.uuid4())[:8]
    batch_queue.completed = []
    batch_queue.failed = []
    batch_queue.running = {}
    batch_queue.paused = False
    batch_queue.total = len(to_crawl)

    for item in to_crawl:
        batch_queue.q.put(item)

    if batch_queue._worker_thread is None or not batch_queue._worker_thread.is_alive():
        batch_queue._worker_thread = threading.Thread(target=_retry_worker, daemon=True)
        batch_queue._worker_thread.start()

    return {
        "message": f"Retrying {len(to_crawl)} error brands in {body.industry}",
        "count": len(to_crawl),
    }


class IndustryRefreshRequest(BaseModel):
    industry: str


@admin_router.post("/industry/refresh")
def refresh_industry(
    body: IndustryRefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    settings = _load_settings()
    cycle_days = settings["refresh_cycle_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=cycle_days)

    outdated = (
        db.query(Brand)
        .filter(
            Brand.status == "done",
            Brand.category == body.industry,
        )
        .all()
    )

    to_refresh = []
    for b in outdated:
        if (
            not b.last_refreshed
            or b.last_refreshed.replace(tzinfo=timezone.utc) < cutoff
        ):
            to_refresh.append(
                {"name": b.name or "", "url": b.url, "category": b.category or ""}
            )

    if not to_refresh:
        return {"message": "No outdated brands", "count": 0}

    batch_queue.max_concurrent = settings["max_concurrent"]
    task_id = batch_queue.start(to_refresh)
    return {
        "task_id": task_id,
        "message": f"Refreshing {len(to_refresh)} brands in {body.industry}",
        "count": len(to_refresh),
    }


@admin_router.post("/industry/refresh-all")
def refresh_all_industry(
    body: IndustryRefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    done_brands = (
        db.query(Brand)
        .filter(Brand.status == "done", Brand.category == body.industry)
        .all()
    )

    if not done_brands:
        return {"message": "No done brands to refresh", "count": 0}

    to_crawl = []
    for b in done_brands:
        b.status = "pending"
        b.error_message = None
        b.updated_at = datetime.now(timezone.utc)
        to_crawl.append(
            {
                "name": b.name or "",
                "url": b.url,
                "category": b.category or "",
                "brand_id": b.id,
            }
        )
    db.commit()

    settings = _load_settings()
    batch_queue.max_concurrent = settings["max_concurrent"]

    batch_queue.task_id = str(uuid.uuid4())[:8]
    batch_queue.completed = []
    batch_queue.failed = []
    batch_queue.running = {}
    batch_queue.paused = False
    batch_queue.total = len(to_crawl)

    for item in to_crawl:
        batch_queue.q.put(item)

    if batch_queue._worker_thread is None or not batch_queue._worker_thread.is_alive():
        batch_queue._worker_thread = threading.Thread(target=_retry_worker, daemon=True)
        batch_queue._worker_thread.start()

    return {
        "message": f"Refreshing all {len(to_crawl)} done brands in {body.industry}",
        "count": len(to_crawl),
    }


# ============================================================
# Brand Management
# ============================================================


@admin_router.get("/brands")
def list_admin_brands(
    page: int = 1,
    per_page: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    query = db.query(Brand)

    if category:
        query = query.filter(Brand.category == category)
    if status:
        query = query.filter(Brand.status == status)
    if q:
        query = query.filter(Brand.name.ilike(f"%{q}%"))

    total = query.count()
    brands = (
        query.order_by(Brand.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "brands": [
            {
                "id": b.id,
                "name": b.name,
                "url": b.url,
                "category": b.category,
                "status": b.status,
                "logo_url": b.logo_url,
                "description": b.description,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None,
                "last_refreshed": b.last_refreshed.isoformat()
                if b.last_refreshed
                else None,
            }
            for b in brands
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None


@admin_router.put("/brands/{brand_id}")
def update_admin_brand(
    brand_id: str,
    body: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if body.name is not None:
        brand.name = body.name
    if body.category is not None:
        brand.category = body.category
    if body.url is not None:
        brand.url = body.url
    if body.description is not None:
        brand.description = body.description

    brand.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(brand)

    return {
        "id": brand.id,
        "name": brand.name,
        "url": brand.url,
        "category": brand.category,
        "status": brand.status,
        "logo_url": brand.logo_url,
        "description": brand.description,
        "created_at": brand.created_at.isoformat() if brand.created_at else None,
        "updated_at": brand.updated_at.isoformat() if brand.updated_at else None,
        "last_refreshed": brand.last_refreshed.isoformat()
        if brand.last_refreshed
        else None,
    }


@admin_router.delete("/brands/{brand_id}")
def delete_admin_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    db.delete(brand)
    db.commit()

    json_path = os.path.join(
        os.path.dirname(__file__), "data", "brands", f"{brand_id}.json"
    )
    if os.path.exists(json_path):
        os.remove(json_path)

    return {"message": "Deleted"}


class BatchDeleteRequest(BaseModel):
    brand_ids: list[str]


@admin_router.post("/brands/batch-delete")
def batch_delete_brands(
    body: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    count = 0
    data_dir = os.path.join(os.path.dirname(__file__), "data", "brands")
    for brand_id in body.brand_ids:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            db.delete(brand)
            count += 1
            json_path = os.path.join(data_dir, f"{brand_id}.json")
            if os.path.exists(json_path):
                os.remove(json_path)
    db.commit()
    return {"message": f"Deleted {count} brands", "count": count}


@admin_router.post("/brands/batch-refresh")
def batch_refresh_brands(
    body: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    count = 0
    for brand_id in body.brand_ids:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            brand.status = "pending"
            brand.error_message = None
            brand.updated_at = datetime.now(timezone.utc)
            db.commit()
            batch_queue.q.put(
                {
                    "name": brand.name or "",
                    "url": brand.url,
                    "category": brand.category or "",
                    "brand_id": brand.id,
                }
            )
            count += 1
    batch_queue.total += count
    batch_queue.ensure_worker()
    return {"message": f"Queued {count} brands for refresh", "count": count}


@admin_router.post("/brands/{brand_id}/refresh")
def refresh_single_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    brand.status = "pending"
    brand.error_message = None
    brand.updated_at = datetime.now(timezone.utc)
    db.commit()

    batch_queue.q.put(
        {
            "name": brand.name or "",
            "url": brand.url,
            "category": brand.category or "",
            "brand_id": brand.id,
        }
    )
    batch_queue.total += 1
    batch_queue.ensure_worker()
    return {"message": "Queued for refresh"}
