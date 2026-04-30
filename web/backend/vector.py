"""ChromaDB vector operations for brand knowledge search."""
import json
import os
import chromadb

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8003"))


def get_chroma_client():
    try:
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    except Exception:
        return chromadb.Client()


def index_brand(brand_id: str, data: dict):
    """Chunk brand JSON and store in ChromaDB."""
    client = get_chroma_client()
    collection_name = f"brand_{brand_id.replace('-', '_')[:50]}"
    
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    
    collection = client.create_collection(name=collection_name)
    
    documents = []
    ids = []
    metadatas = []
    
    brand_name = data.get("identity", {}).get("name", "Unknown")
    
    # Chunk by dimension
    dimensions = [
        "identity", "offerings", "differentiation", "trust",
        "access", "content", "perception",
        "decision_factors", "vitality"
    ]
    
    for dim in dimensions:
        if dim in data and data[dim]:
            text = json.dumps(data[dim], ensure_ascii=False, indent=2)
            # Split large sections into ~1000 char chunks
            if len(text) > 1500:
                for i in range(0, len(text), 1000):
                    chunk = text[i:i+1000]
                    chunk_id = f"{brand_id}_{dim}_{i}"
                    documents.append(f"[{brand_name}] [{dim}] {chunk}")
                    ids.append(chunk_id)
                    metadatas.append({"brand_id": brand_id, "brand_name": brand_name, "dimension": dim})
            else:
                documents.append(f"[{brand_name}] [{dim}] {text}")
                ids.append(f"{brand_id}_{dim}")
                metadatas.append({"brand_id": brand_id, "brand_name": brand_name, "dimension": dim})
    
    if documents:
        collection.add(documents=documents, ids=ids, metadatas=metadatas)


def search_brand(brand_id: str, query: str, n_results: int = 5):
    """Search within a brand's knowledge base."""
    client = get_chroma_client()
    collection_name = f"brand_{brand_id.replace('-', '_')[:50]}"
    
    try:
        collection = client.get_collection(name=collection_name)
        results = collection.query(query_texts=[query], n_results=n_results)
        return results
    except Exception:
        return None


def search_all_brands(query: str, n_results: int = 5):
    """Search across all brand collections."""
    client = get_chroma_client()
    all_results = []
    
    try:
        collections = client.list_collections()
        for col in collections:
            if col.name.startswith("brand_"):
                results = col.query(query_texts=[query], n_results=2)
                if results and results["documents"]:
                    for i, doc in enumerate(results["documents"][0]):
                        all_results.append({
                            "document": doc,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "distance": results["distances"][0][i] if results["distances"] else 0
                        })
    except Exception:
        pass
    
    all_results.sort(key=lambda x: x.get("distance", 999))
    return all_results[:n_results]


def delete_brand_index(brand_id: str):
    """Delete a brand's vector index."""
    client = get_chroma_client()
    collection_name = f"brand_{brand_id.replace('-', '_')[:50]}"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
