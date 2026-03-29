"""Step 3: Web search expansion via Tavily API."""
import requests
from .config import TAVILY_API_KEY, TAVILY_ENDPOINT


def search_expand(clues: dict) -> list[dict]:
    """Run web searches based on extracted clues to gather more context."""
    if not TAVILY_API_KEY:
        print("⏭️  Skipping web search (TAVILY_API_KEY not set)")
        return []

    brand = clues.get("brand_name", "")
    company = clues.get("legal_name", "")
    category = clues.get("category", "")

    if not brand and not company:
        print("⏭️  Skipping web search (no brand name extracted)")
        return []

    queries = []
    name = brand or company
    queries.append(f"{name}")
    queries.append(f"{name} 评价 review")
    if company and company != brand:
        queries.append(f"{company} 融资 投资")
    if category:
        queries.append(f"{name} {category}")
    queries.append(f"{name} 活动 新品 发布 2026")

    print(f"🔎 Running {len(queries)} web searches...")
    results = []
    for q in queries:
        try:
            resp = requests.post(
                TAVILY_ENDPOINT,
                json={"query": q, "max_results": 5, "include_answer": True},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {TAVILY_API_KEY}",
                },
                timeout=30,
            )
            if resp.status_code == 401:
                print(f"   ❌ Tavily auth failed, skipping remaining searches")
                break
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer", "")
            search_results = data.get("results", [])
            results.append({
                "query": q,
                "answer": answer,
                "results": [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")} for r in search_results],
            })
            print(f"   ✅ '{q}' → {len(search_results)} results")
        except Exception as e:
            print(f"   ⚠️  Search '{q}' failed: {e}")

    return results
