"""MCP Server endpoint for Brand2Context (Streamable HTTP)."""

import json
import os
from models import SessionLocal, Brand

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "brands")

MCP_TOOLS = [
    {
        "name": "list_brands",
        "description": "List all available brand knowledge bases",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_brand_info",
        "description": "Get full brand knowledge base by brand name",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand_name": {"type": "string", "description": "Brand name to look up"}
            },
            "required": ["brand_name"],
        },
    },
    {
        "name": "search_brand",
        "description": "Semantic search across all brand knowledge bases",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "resolve_brand_id",
        "description": "Resolve brand name to brand ID and metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand_name": {"type": "string", "description": "Brand name to resolve"}
            },
            "required": ["brand_name"],
        },
    },
    {
        "name": "get_brand_context",
        "description": "Get relevant brand knowledge context based on query",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand_id_or_slug": {
                    "type": "string",
                    "description": "Brand ID or slug",
                },
                "query": {
                    "type": "string",
                    "description": "Optional query to search for relevant context",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens to return",
                    "default": 5000,
                },
            },
            "required": ["brand_id_or_slug"],
        },
    },
]


def handle_mcp_request(request_body: dict) -> dict:
    """Handle a JSON-RPC MCP request."""
    method = request_body.get("method", "")
    req_id = request_body.get("id")
    params = request_body.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "brand2context", "version": "0.1.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
                ]
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _call_tool(name: str, arguments: dict):
    db = SessionLocal()
    try:
        if name == "list_brands":
            brands = db.query(Brand).filter(Brand.status == "done").all()
            return [{"id": b.id, "name": b.name, "url": b.url} for b in brands]

        elif name == "get_brand_info":
            brand_name = arguments.get("brand_name", "")
            brand = (
                db.query(Brand)
                .filter(Brand.name.ilike(f"%{brand_name}%"), Brand.status == "done")
                .first()
            )
            if not brand:
                return {"error": f"Brand '{brand_name}' not found"}
            json_path = os.path.join(DATA_DIR, f"{brand.id}.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    return json.load(f)
            return {"error": "Brand data file not found"}

        elif name == "search_brand":
            query = arguments.get("query", "")
            try:
                from vector import search_all_brands

                results = search_all_brands(query)
                return results
            except Exception as e:
                return {"error": f"Search failed: {str(e)}"}

        elif name == "resolve_brand_id":
            brand_name = arguments.get("brand_name", "")
            brands = (
                db.query(Brand)
                .filter(
                    Brand.name.ilike(f"%{brand_name}%"),
                    Brand.status == "done",
                    Brand.is_public == True,
                )
                .all()
            )
            return [
                {
                    "id": b.id,
                    "slug": b.slug,
                    "name": b.name,
                    "category": b.category,
                    "description": b.description,
                }
                for b in brands
            ]

        elif name == "get_brand_context":
            brand_id_or_slug = arguments.get("brand_id_or_slug", "")
            query = arguments.get("query", "")
            max_tokens = arguments.get("max_tokens", 5000)

            brand = (
                db.query(Brand)
                .filter(
                    (Brand.id == brand_id_or_slug) | (Brand.slug == brand_id_or_slug)
                )
                .first()
            )

            if not brand:
                return {"error": f"Brand '{brand_id_or_slug}' not found"}

            json_path = os.path.join(DATA_DIR, f"{brand.id}.json")
            if not os.path.exists(json_path):
                return {"error": "Brand data file not found"}

            with open(json_path, "r", encoding="utf-8") as f:
                knowledge = json.load(f)

            if query:
                try:
                    from vector import search_brand

                    results = search_brand(brand.id, query, n_results=10)
                    if results and results.get("documents") and results["documents"][0]:
                        chunks = results["documents"][0]
                        context = "\n\n".join(chunks)
                        if len(context) > max_tokens * 4:
                            context = context[: max_tokens * 4]
                        return {
                            "brand_id": brand.id,
                            "slug": brand.slug,
                            "name": brand.name,
                            "context": context,
                        }
                except Exception:
                    pass

                return {"error": "Vector search not available, use brand data endpoint"}
            else:
                identity = knowledge.get("identity", {})
                summary = {
                    "brand_id": brand.id,
                    "slug": brand.slug,
                    "name": identity.get("name", brand.name),
                    "tagline": identity.get("tagline", ""),
                    "positioning": identity.get("positioning", ""),
                    "description": identity.get("description", ""),
                }

                key_sections = []
                for section in ["offerings", "values", "achievements", "contact"]:
                    if section in knowledge:
                        key_sections.append(
                            f"{section}: {json.dumps(knowledge[section], ensure_ascii=False)}"
                        )

                summary_text = json.dumps(summary, ensure_ascii=False)
                if key_sections:
                    summary_text += "\n\n" + "\n\n".join(key_sections)

                if len(summary_text) > max_tokens * 4:
                    summary_text = summary_text[: max_tokens * 4]

                return {"context": summary_text}

        return {"error": f"Unknown tool: {name}"}
    finally:
        db.close()
