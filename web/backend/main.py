"""Brand2Context FastAPI application."""
import json
import os
import uuid
import threading
import copy
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import init_db, get_db, Brand, ApiCallLog, SessionLocal
from tasks import run_brand_pipeline
from mcp_server import handle_mcp_request

MINIMAX_API_KEY = os.getenv(
    "MINIMAX_API_KEY",
    "sk-cp-49r5TFMzeb7-z-HCbtIPK3h7NZPVs8QJIPVIBC9S3JDjeHq4pKU6YZ-srAyN1YH3-LR6wS0ot4f6xEcqR34SsBpE-yPuW-9kb_yGlDRaive4lhwduA3UAZs",
)

app = FastAPI(title="Brand2Context API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "brands")
os.makedirs(DATA_DIR, exist_ok=True)


@app.on_event("startup")
def startup():
    os.makedirs("data", exist_ok=True)
    init_db()


# --- Pydantic schemas ---

class BrandCreate(BaseModel):
    url: str

class BrandResponse(BaseModel):
    id: str
    name: Optional[str] = None
    url: str
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def brand_to_response(b: Brand) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "url": b.url,
        "status": b.status,
        "error_message": b.error_message,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


# --- API Endpoints ---

@app.post("/api/brands")
def create_brand(body: BrandCreate, db: Session = Depends(get_db)):
    url = body.url
    if not url.startswith("http"):
        url = "https://" + url

    brand_id = str(uuid.uuid4())
    brand = Brand(id=brand_id, url=url, status="pending")
    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Start background task
    thread = threading.Thread(target=run_brand_pipeline, args=(brand_id, url), daemon=True)
    thread.start()

    return brand_to_response(brand)


@app.get("/api/brands")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).order_by(Brand.created_at.desc()).all()
    return [brand_to_response(b) for b in brands]


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
    return {"id": brand.id, "status": brand.status, "error_message": brand.error_message}


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
            return {
                "documents": results.get("documents", [[]])[0],
                "distances": results.get("distances", [[]])[0],
            }
        return {"documents": [], "distances": []}
    except Exception as e:
        return {"documents": [], "distances": [], "error": str(e)}


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

    system_prompt = (
        "You are a brand knowledge assistant. Answer questions about this brand based ONLY "
        "on the provided knowledge base data. Be concise and accurate. If the data doesn't "
        "contain the answer, say so.\n\n"
        f"Brand Knowledge Base:\n{json.dumps(knowledge, ensure_ascii=False, indent=2)}"
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
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "Unable to get response")
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
        "last_accessed": log.last_accessed.isoformat() if log and log.last_accessed else None,
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
