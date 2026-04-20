"""Social media public data search without login."""

import time


def search_social_public(brand_name: str, url: str = "") -> list[dict]:
    """Search for brand's social media public data via Metaso.

    Does not require login. Uses Metaso search engine to find public
    content on Weibo, Xiaohongshu, and other platforms.

    Returns:
        list of search result dicts, same format as web_searcher results:
        [{"query": "...", "results": [...], "source": "social_metaso", "answer": "..."}]
    """
    from .web_searcher import _search_metaso

    queries = []
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in brand_name)

    queries.append(f'"{brand_name}" 百科 创始 成立 总部 创始人')
    queries.append(f'"{brand_name}" Wikipedia founded headquarters')
    queries.append(f'"{brand_name}" 微博 最新')
    queries.append(f'"{brand_name}" 小红书 种草 测评')

    if has_chinese:
        queries.append(f'"{brand_name}" 2024 2025 活动 新品发布 联名')
        queries.append(f'"{brand_name}" 抖音 直播 带货')
    else:
        queries.append(f'"{brand_name}" weibo latest')
        queries.append(f'"{brand_name}" 2024 2025 活动 新品发布 联名')
        queries.append(f'"{brand_name}" Douyin livestream')

    social_search_results = []
    assigned_urls = set()

    for query in queries:
        try:
            result = _search_metaso(query, size=5)
            if result.get("results"):
                filtered = []
                for r in result["results"]:
                    r_url = r.get("url", "")
                    if r_url and r_url not in assigned_urls:
                        filtered.append(r)
                        assigned_urls.add(r_url)
                if filtered:
                    social_search_results.append(
                        {
                            "query": query,
                            "results": filtered,
                            "source": "social_metaso",
                            "answer": result.get("answer", ""),
                        }
                    )
            time.sleep(1)
        except Exception:
            time.sleep(1)
            continue

    return social_search_results
