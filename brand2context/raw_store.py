"""Raw data storage for brand crawl results."""

import json
import os
from datetime import datetime, timezone
from typing import Optional


class RawStore:
    """Manages raw crawled data for a brand."""

    def __init__(self, brand_id: str, base_dir: str = "data/brands"):
        self.brand_id = brand_id
        self.base_dir = os.path.join(base_dir, brand_id)
        self.pages_dir = os.path.join(self.base_dir, "raw", "pages")
        self.search_dir = os.path.join(self.base_dir, "raw", "search")
        self.social_dir = os.path.join(self.base_dir, "raw", "social")
        self.manifest_path = os.path.join(self.base_dir, "manifest.json")
        os.makedirs(self.pages_dir, exist_ok=True)
        os.makedirs(self.search_dir, exist_ok=True)
        os.makedirs(self.social_dir, exist_ok=True)

    def add_page(
        self, url: str, title: str, content: str, source: str = "link2context"
    ) -> str:
        """Store a crawled page. Returns the filename."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.strip("/").replace("/", "_") or "homepage"
        filename = f"{path[:60]}.md"
        filepath = os.path.join(self.pages_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(
                f"---\nurl: {url}\ntitle: {title}\nsource: {source}\ncrawled_at: {datetime.now(timezone.utc).isoformat()}\n---\n\n{content}"
            )
        return filename

    def add_search_result(
        self, query: str, results: list[dict], source: str = "tavily", answer: str = ""
    ) -> str:
        """Store search results. Returns the filename."""
        safe_query = "".join(c if c.isalnum() or c in "_ -" else "_" for c in query)[
            :50
        ]
        filename = f"{source}_{safe_query}.json"
        filepath = os.path.join(self.search_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "query": query,
                    "source": source,
                    "answer": answer,
                    "results": results,
                    "searched_at": datetime.now(timezone.utc).isoformat(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        return filename

    def add_social(self, platform: str, data: list[dict]) -> str:
        """Store social media data."""
        filename = f"{platform}.json"
        filepath = os.path.join(self.social_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filename

    def get_all_pages(self) -> list[dict]:
        """Read all stored pages. Returns list of {url, title, content, filename}."""
        pages = []
        for filename in sorted(os.listdir(self.pages_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(self.pages_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
            url, title, content = "", "", raw
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) >= 3:
                    meta = parts[1]
                    content = parts[2].strip()
                    for line in meta.strip().split("\n"):
                        if line.startswith("url:"):
                            url = line[4:].strip()
                        elif line.startswith("title:"):
                            title = line[6:].strip()
            pages.append(
                {"url": url, "title": title, "content": content, "filename": filename}
            )
        return pages

    def get_all_search_results(self) -> list[dict]:
        """Read all stored search results."""
        results = []
        for filename in sorted(os.listdir(self.search_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.search_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                results.append(json.load(f))
        return results

    def get_all_social(self) -> list[dict]:
        """Read all stored social data."""
        all_social = []
        for filename in sorted(os.listdir(self.social_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.social_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                all_social.extend(json.load(f))
        return all_social

    def get_summary(self) -> dict:
        """Get a summary of stored data for LLM review."""
        pages = self.get_all_pages()
        searches = self.get_all_search_results()

        page_summaries = []
        for p in pages:
            page_summaries.append(
                {
                    "filename": p["filename"],
                    "url": p["url"],
                    "title": p["title"],
                    "chars": len(p["content"]),
                    "preview": p["content"][:200],
                }
            )

        search_summaries = []
        for s in searches:
            search_summaries.append(
                {
                    "query": s.get("query", ""),
                    "source": s.get("source", ""),
                    "result_count": len(s.get("results", [])),
                    "has_answer": bool(s.get("answer", "")),
                }
            )

        return {
            "total_pages": len(pages),
            "total_searches": len(searches),
            "pages": page_summaries,
            "searches": search_summaries,
        }

    def update_manifest(
        self,
        round_num: int,
        round_type: str,
        pages_added: int,
        searches_added: int,
        reason: str = "",
    ):
        """Update the manifest with round information."""
        manifest = {
            "brand_id": self.brand_id,
            "rounds": [],
            "total_pages": 0,
            "total_searches": 0,
        }
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        manifest["rounds"].append(
            {
                "round": round_num,
                "type": round_type,
                "reason": reason,
                "pages_added": pages_added,
                "searches_added": searches_added,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        manifest["total_pages"] = len(os.listdir(self.pages_dir))
        manifest["total_searches"] = len(os.listdir(self.search_dir))
        manifest["completion_rounds"] = round_num

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
