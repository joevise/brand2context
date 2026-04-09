"""Brand2Context FastAPI application."""

import json
import os
import uuid
import threading
import copy
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
import jwt
import bcrypt
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import init_db, get_db, Brand, ApiCallLog, User, SessionLocal
from tasks import run_brand_pipeline
from mcp_server import handle_mcp_request
from admin import admin_router

JWT_SECRET = os.getenv("JWT_SECRET", "brand2context-dev-secret")


def _recover_stuck_brands():
    """On startup, reset any brands stuck in processing/pending (from previous container lifecycle)."""
    try:
        db = SessionLocal()
        stuck = db.query(Brand).filter(Brand.status.in_(["processing", "pending"])).all()
        if stuck:
            for b in stuck:
                b.status = "error"
                b.progress_step = "error"
                b.error_message = "Auto-reset: task was interrupted by server restart"
                b.updated_at = datetime.now(timezone.utc)
            db.commit()
            print(f"🔄 Startup recovery: reset {len(stuck)} stuck brands to error status")
        db.close()
    except Exception as e:
        print(f"⚠️ Startup recovery failed: {e}")

MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
    "sk-cp-49r5TFMzeb7-z-HCbtIPK3h7NZPVs8QJIPVIBC9S3JDjeHq4pKU6YZ-srAyN1YH3-LR6wS0ot4f6xEcqR34SsBpE-yPuW-9kb_yGlDRaive4lhwduA3UAZs",
)


app = FastAPI(title="Brand2Context API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "brands")
os.makedirs(DATA_DIR, exist_ok=True)


@app.on_event("startup")
def startup():
    os.makedirs("data", exist_ok=True)
    init_db()
    # Auto-recover stuck brands after container restart
    _recover_stuck_brands()


# --- Pydantic schemas ---


class BrandCreate(BaseModel):
    url: str
    name: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None


class BrandResponse(BaseModel):
    id: str
    name: Optional[str] = None
    url: str
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    logo_url: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = True

    class Config:
        from_attributes = True


class BrandSearchResponse(BaseModel):
    brands: list
    total: int
    page: int
    per_page: int


class BatchBrandCreate(BaseModel):
    brands: list


class UserRegister(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    is_admin: bool = False
    created_at: str


def brand_to_response(b: Brand) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "url": b.url,
        "status": b.status,
        "progress_step": b.progress_step if b.progress_step else "pending",
        "error_message": b.error_message,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        "logo_url": b.logo_url,
        "category": b.category,
        "slug": b.slug,
        "description": b.description,
        "is_public": b.is_public if b.is_public is not None else True,
    }


# --- API Endpoints ---


def get_current_user(
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
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@app.post("/api/auth/register")
def register(body: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=body.email, password_hash=password_hash, name=body.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = jwt.encode({"user_id": user.id}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@app.post("/api/auth/login")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"user_id": user.id}, JWT_SECRET, algorithm="HS256")
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat()
        if current_user.created_at
        else None,
    }


@app.post("/api/brands")
def create_brand(body: BrandCreate, db: Session = Depends(get_db)):
    url = body.url
    if not url.startswith("http"):
        url = "https://" + url

    brand_id = str(uuid.uuid4())
    brand = Brand(
        id=brand_id,
        url=url,
        status="pending",
        progress_step="crawling",
        category=body.category,
        name=body.name,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)

    thread = threading.Thread(
        target=run_brand_pipeline, args=(brand_id, url), daemon=True
    )
    thread.start()

    return brand_to_response(brand)


@app.get("/api/brands")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).order_by(Brand.created_at.desc()).all()
    return [brand_to_response(b) for b in brands]


# --- Brand Search (MUST be before {brand_id} route!) ---
@app.get("/api/brands/search")
def search_brands_early(
    q: str = "",
    category: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Brand).filter(Brand.status == "done", Brand.is_public == True)

    if q:
        query = query.filter(Brand.name.ilike(f"%{q}%"))
    if category:
        query = query.filter(Brand.category == category)

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
                "slug": b.slug,
                "logo_url": b.logo_url,
                "category": b.category,
                "description": b.description,
                "url": b.url,
            }
            for b in brands
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# --- Get Brand by Slug (MUST be before {brand_id} route!) ---
@app.get("/api/brands/by-slug/{slug}")
def get_brand_by_slug_early(slug: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    _record_call(brand.id)

    result = brand_to_response(brand)
    json_path = os.path.join(DATA_DIR, f"{brand.id}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            result["data"] = json.load(f)
    return result


# --- Batch Create Brands (MUST be before {brand_id} route!) ---
@app.post("/api/brands/batch")
def batch_create_brands_early(body: BatchBrandCreate, db: Session = Depends(get_db)):
    created_ids = []

    for item in body.brands:
        url = item.get("url", "")
        if not url:
            continue
        if not url.startswith("http"):
            url = "https://" + url

        brand_id = str(uuid.uuid4())
        brand = Brand(
            id=brand_id,
            url=url,
            status="pending",
            category=item.get("category"),
        )
        db.add(brand)
        db.commit()

        thread = threading.Thread(
            target=run_brand_pipeline, args=(brand_id, url), daemon=True
        )
        thread.start()

        created_ids.append(brand_id)

    return {"created_ids": created_ids}


@app.get("/api/brands/{brand_id}")
def get_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    result = brand_to_response(brand)

    # Track API call
    _record_call(brand_id)

    # Include full JSON data if available
    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            result["data"] = json.load(f)

    return result


@app.delete("/api/brands/{brand_id}")
def delete_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    db.delete(brand)
    db.commit()

    # Delete JSON file
    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    if os.path.exists(json_path):
        os.remove(json_path)

    # Delete vector index
    try:
        from vector import delete_brand_index

        delete_brand_index(brand_id)
    except Exception:
        pass

    return {"message": "Deleted"}


@app.get("/api/brands/{brand_id}/status")
def get_brand_status(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return {
        "id": brand.id,
        "status": brand.status,
        "progress_step": brand.progress_step if brand.progress_step else "pending",
        "error_message": brand.error_message,
    }


@app.get("/api/brands/{brand_id}/search")
def search_brand_endpoint(brand_id: str, q: str = "", db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    try:
        from vector import search_brand

        results = search_brand(brand_id, q)
        if results:
            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            return {
                "documents": docs,
                "distances": distances,
                "metadatas": metadatas,
            }
        return {"documents": [], "distances": [], "metadatas": []}
    except Exception as e:
        return {"documents": [], "distances": [], "metadatas": [], "error": str(e)}


# --- Categories List ---
@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    brands = (
        db.query(Brand.category, func.count(Brand.id))
        .filter(
            Brand.status == "done", Brand.is_public == True, Brand.category.isnot(None)
        )
        .group_by(Brand.category)
        .all()
    )

    return {"categories": [{"name": name, "count": count} for name, count in brands]}


# --- Stats Overview ---
@app.get("/api/stats/overview")
def get_stats_overview(db: Session = Depends(get_db)):
    total_brands = (
        db.query(Brand).filter(Brand.status == "done", Brand.is_public == True).count()
    )
    total_categories = (
        db.query(Brand.category)
        .filter(
            Brand.status == "done", Brand.is_public == True, Brand.category.isnot(None)
        )
        .distinct()
        .count()
    )
    total_api_calls = (
        db.query(func.sum(ApiCallLog.call_count))
        .filter(
            ApiCallLog.brand_id.in_(
                db.query(Brand.id).filter(
                    Brand.status == "done", Brand.is_public == True
                )
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_brands": total_brands,
        "total_categories": total_categories,
        "total_api_calls": total_api_calls,
    }


# --- Fetch Logo ---
@app.post("/api/brands/{brand_id}/fetch-logo")
def fetch_brand_logo(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    logo_url = None

    try:
        from urllib.parse import urlparse

        domain = urlparse(brand.url).netloc
        if domain.startswith("www."):
            domain = domain[4:]

        clearbit_url = f"https://logo.clearbit.com/{domain}"
        resp = httpx.get(clearbit_url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            logo_url = clearbit_url
    except Exception:
        pass

    if not logo_url:
        try:
            resp = httpx.get(brand.url, timeout=10.0, follow_redirects=True)
            html = resp.text

            import re

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
                        logo_url = f"{urlparse(brand.url).scheme}://{urlparse(brand.url).netloc}{icon_href}"
        except Exception:
            pass

    if logo_url:
        brand.logo_url = logo_url
        db.commit()

    return {"logo_url": logo_url, "brand_id": brand_id}


# --- Batch Create Brands ---
@app.post("/api/brands/batch")
def batch_create_brands(body: BatchBrandCreate, db: Session = Depends(get_db)):
    created_ids = []

    for item in body.brands:
        url = item.get("url", "")
        if not url:
            continue
        if not url.startswith("http"):
            url = "https://" + url

        brand_id = str(uuid.uuid4())
        brand = Brand(
            id=brand_id,
            url=url,
            status="pending",
            category=item.get("category"),
        )
        db.add(brand)
        db.commit()

        thread = threading.Thread(
            target=run_brand_pipeline, args=(brand_id, url), daemon=True
        )
        thread.start()

        created_ids.append(brand_id)

    return {"created_ids": created_ids}


# --- Helper: record API call ---


def _record_call(brand_id: str):
    """Increment API call counter for a brand."""
    try:
        db = SessionLocal()
        log = db.query(ApiCallLog).filter(ApiCallLog.brand_id == brand_id).first()
        if log:
            log.call_count += 1
            log.last_accessed = datetime.now(timezone.utc)
        else:
            log = ApiCallLog(brand_id=brand_id, call_count=1)
            db.add(log)
        db.commit()
        db.close()
    except Exception:
        pass


# --- Chat Endpoint ---


class ChatRequest(BaseModel):
    message: str


@app.post("/api/brands/{brand_id}/chat")
def chat_with_brand(brand_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=400, detail="Brand knowledge not ready")

    with open(json_path, "r", encoding="utf-8") as f:
        knowledge = json.load(f)

    # Try vector search first for more relevant context
    context_text = None
    try:
        from vector import search_brand

        vector_results = search_brand(brand_id, body.message, n_results=5)
        if (
            vector_results
            and vector_results.get("documents")
            and vector_results["documents"][0]
        ):
            chunks = vector_results["documents"][0]
            # Always include identity context
            identity = knowledge.get("identity", {})
            identity_ctx = f"Brand: {identity.get('name', 'Unknown')}\nTagline: {identity.get('tagline', '')}\nPositioning: {identity.get('positioning', '')}"
            relevant = "\n\n".join(chunks)
            context_text = f"{identity_ctx}\n\nRelevant knowledge:\n{relevant}"
    except Exception:
        pass

    if not context_text:
        # Fallback to full JSON
        context_text = f"Brand Knowledge Base:\n{json.dumps(knowledge, ensure_ascii=False, indent=2)}"

    system_prompt = (
        "你是品牌知识库助手。请根据提供的品牌知识库数据回答问题，简洁准确。如果数据中没有相关信息，请说明。\n\n"
        f"{context_text}"
    )

    try:
        resp = httpx.post(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.7",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": body.message},
                ],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "Unable to get response")
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# --- Editable Knowledge ---


@app.put("/api/brands/{brand_id}/knowledge")
def update_knowledge(brand_id: str, request: Request, db: Session = Depends(get_db)):
    import asyncio

    loop = asyncio.new_event_loop()
    body = loop.run_until_complete(request.json())
    loop.close()

    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    existing = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    def deep_merge(base, updates):
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    merged = deep_merge(copy.deepcopy(existing), body)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    brand.updated_at = datetime.now(timezone.utc)
    db.commit()

    return merged


# --- Public Knowledge ---


@app.get("/api/brands/{brand_id}/public")
def get_public_knowledge(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=400, detail="Knowledge not ready")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _record_call(brand_id)
    return {"brand_id": brand_id, "name": brand.name, "url": brand.url, "data": data}


@app.get("/api/brands/{brand_id}/embed-config")
def get_embed_config(brand_id: str, request: Request, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    base = str(request.base_url).rstrip("/")
    return {
        "brand_id": brand_id,
        "brand_name": brand.name,
        "mcp_endpoint": f"{base}/mcp",
        "api_endpoint": f"{base}/api/brands/{brand_id}",
        "public_endpoint": f"{base}/api/brands/{brand_id}/public",
        "instructions": [
            "1. Use the MCP endpoint with any MCP-compatible AI client",
            "2. Or call the API endpoint directly to get brand knowledge JSON",
            "3. Configure your AI agent to use the brand name for lookups",
        ],
    }


# --- Stats ---


@app.get("/api/brands/{brand_id}/stats")
def get_brand_stats(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    log = db.query(ApiCallLog).filter(ApiCallLog.brand_id == brand_id).first()
    return {
        "brand_id": brand_id,
        "call_count": log.call_count if log else 0,
        "last_accessed": log.last_accessed.isoformat()
        if log and log.last_accessed
        else None,
    }


DIMENSION_FIELD_MAP = {
    "identity": [
        "name",
        "tagline",
        "positioning",
        "category",
        "founded",
        "headquarters",
        "founder",
        "scale",
        "mission",
        "vision",
        "values",
        "brand_story",
    ],
    "offerings": [],
    "differentiation": [
        "unique_selling_points",
        "competitive_advantages",
        "technology_highlights",
        "awards",
    ],
    "trust": ["certifications", "partnerships", "user_stats", "testimonials"],
    "experience": ["warranty", "return_policy", "onboarding", "community", "faq"],
    "access": ["official_website", "contact", "social_media"],
    "content": ["latest_news", "key_announcements", "blog_posts"],
    "perception": [
        "personality_traits",
        "brand_tone",
        "price_positioning",
        "price_benchmark",
        "category_association",
        "primary_audience",
        "usage_occasions",
    ],
    "decision_factors": [
        "category_key_factors",
        "perceived_risks",
        "switching_cost",
        "trial_barrier",
    ],
    "vitality": [
        "content_frequency",
        "last_product_launch",
        "last_campaign",
        "growth_signal",
        "community_size",
        "nps_or_satisfaction",
        "market_position",
        "industry_role",
    ],
    "campaigns": ["ongoing", "recent", "upcoming", "annual_events"],
}


def _evaluate_dimension(dim: str, data: any) -> dict:
    fields = DIMENSION_FIELD_MAP.get(dim, [])
    filled = []
    missing = []
    score = 0

    if data is None or data == {}:
        return {
            "score": 0,
            "filled": [],
            "missing": fields or [],
            "status": "empty",
            "reason": "No data extracted",
        }

    if dim == "offerings":
        if isinstance(data, list) and len(data) > 0:
            filled_count = sum(
                1 for item in data if isinstance(item, dict) and any(item.values())
            )
            score = min(100, int(filled_count / len(data) * 100))
            filled = [f"item_{i}" for i in range(len(data))]
            missing = []
            status = "complete" if filled_count == len(data) else "partial"
            reason = f"{filled_count}/{len(data)} offerings with data"
        else:
            score = 0
            missing = ["offerings list"]
            status = "empty"
            reason = "No offerings data"
    else:
        for field in fields:
            val = data.get(field) if isinstance(data, dict) else None
            if val and val != [] and val != {} and val != "":
                filled.append(field)
            else:
                missing.append(field)

        if fields:
            score = int(len(filled) / len(fields) * 100)
        else:
            score = 100 if data else 0

        if score == 100:
            status = "complete"
            reason = "All fields filled"
        elif score >= 50:
            status = "partial"
            reason = f"{len(filled)}/{len(fields)} fields filled"
        elif score > 0:
            status = "sparse"
            reason = f"Only {len(filled)}/{len(fields)} fields filled"
        else:
            status = "empty"
            reason = "No meaningful data extracted"

    return {
        "score": score,
        "filled": filled,
        "missing": missing,
        "status": status,
        "reason": reason,
    }


@app.get("/api/brands/{brand_id}/diagnosis")
def get_brand_diagnosis(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    json_path = os.path.join(DATA_DIR, f"{brand_id}.json")
    hashes_path = os.path.join(DATA_DIR, f"{brand_id}_hashes.json")

    crawl_info = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        crawl_info["data_file_exists"] = True
        crawl_info["generated_at"] = data.get("generated_at")
        crawl_info["schema_version"] = data.get("schema_version")
    else:
        crawl_info["data_file_exists"] = False

    if os.path.exists(hashes_path):
        with open(hashes_path, "r", encoding="utf-8") as f:
            hashes_data = json.load(f)
        crawl_info["last_crawled"] = hashes_data.get("timestamp")

    dimensions = [
        "identity",
        "offerings",
        "differentiation",
        "trust",
        "experience",
        "access",
        "content",
        "perception",
        "decision_factors",
        "vitality",
        "campaigns",
    ]
    dim_results = {}
    total_score = 0

    if crawl_info["data_file_exists"]:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for dim in dimensions:
            dim_data = data.get(dim)
            eval_result = _evaluate_dimension(dim, dim_data)
            dim_results[dim] = eval_result
            total_score += eval_result["score"]
        overall_score = int(total_score / len(dimensions))
    else:
        for dim in dimensions:
            dim_results[dim] = {
                "score": 0,
                "filled": [],
                "missing": DIMENSION_FIELD_MAP.get(dim, []),
                "status": "missing",
                "reason": "No data file found",
            }
        overall_score = 0

    return {
        "brand_id": brand_id,
        "brand_name": brand.name,
        "url": brand.url,
        "status": brand.status,
        "overall_score": overall_score,
        "dimensions": dim_results,
        "crawl_info": crawl_info,
    }


# --- MCP Endpoint ---


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    body = await request.json()
    result = handle_mcp_request(body)
    return JSONResponse(content=result)


# --- Health ---


@app.get("/health")
def health():
    return {"status": "ok", "service": "brand2context-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
