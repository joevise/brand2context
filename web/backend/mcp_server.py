"""MCP Server endpoint for Brand2Context (Streamable HTTP)."""
import json
import os
from models import SessionLocal, Brand

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "brands")

# MCP tool definitions
MCP_TOOLS = [
    {
        "name": "list_brands",
        "description": "List all available brand knowledge bases",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_brand_info",
        "description": "Get full brand knowledge base by brand name",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand_name": {"type": "string", "description": "Brand name to look up"}
            },
            "required": ["brand_name"]
        }
    },
    {
        "name": "search_brand",
        "description": "Semantic search across all brand knowledge bases",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
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
                "serverInfo": {"name": "brand2context", "version": "0.1.0"}
            }
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS}
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def _call_tool(name: str, arguments: dict):
    db = SessionLocal()
    try:
        if name == "list_brands":
            brands = db.query(Brand).filter(Brand.status == "done").all()
            return [{"id": b.id, "name": b.name, "url": b.url} for b in brands]

        elif name == "get_brand_info":
            brand_name = arguments.get("brand_name", "")
            brand = db.query(Brand).filter(
                Brand.name.ilike(f"%{brand_name}%"),
                Brand.status == "done"
            ).first()
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

        return {"error": f"Unknown tool: {name}"}
    finally:
        db.close()
