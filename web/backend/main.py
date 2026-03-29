"""Brand2Context FastAPI application."""
import json
import os
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import init_db, get_db, Brand
from tasks import run_brand_pipeline
from mcp_server import handle_mcp_request

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
