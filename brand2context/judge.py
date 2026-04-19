"""LLM judge — evaluates raw data completeness and issues fill commands."""

from .llm import chat_json

DIMENSIONS = [
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


def judge_completeness(
    brand_name: str, brand_url: str, category: str, raw_summary: dict
) -> dict:
    """Ask LLM to evaluate data completeness and suggest gap-filling actions.

    Returns:
    {
        "scores": {"identity": 8, "offerings": 3, ...},
        "overall_score": 6.5,
        "gaps": [
            {"dimension": "offerings", "missing": "缺少产品列表", "action": "search", "query": "品牌名 TOP产品"},
            {"dimension": "trust", "missing": "缺合作伙伴", "action": "crawl", "target": "/partners"},
        ],
        "is_sufficient": false
    }
    """
    pages_text = ""
    for p in raw_summary.get("pages", [])[:30]:
        pages_text += f"- {p['filename']} ({p['chars']} chars): {p['title']} — {p['url']}\n  预览: {p['preview'][:100]}...\n"

    searches_text = ""
    for s in raw_summary.get("searches", []):
        searches_text += (
            f'- [{s["source"]}] "{s["query"]}" → {s["result_count"]} results\n'
        )

    prompt = f"""你是品牌知识库质量审查员。请评估以下品牌的已抓取数据是否足以生成高质量的品牌知识库。

## 品牌信息
- 名称: {brand_name}
- 官网: {brand_url}
- 品类: {category}

## 已抓取的网页 ({raw_summary["total_pages"]} 页)
{pages_text if pages_text else "(无网页数据)"}

## 已搜索的结果 ({raw_summary["total_searches"]} 组)
{searches_text if searches_text else "(无搜索数据)"}

## 请评估以下 11 个维度的数据充足度（0-10 分），并指出缺失部分和补充建议：

维度说明：
- identity: 品牌身份（名称、创始人、总部、使命、愿景、品牌故事）
- offerings: 产品服务（具体产品列表、功能特性、价格范围 — 至少需要 TOP 5 产品）
- differentiation: 差异化（独特卖点、竞争优势、技术亮点）
- trust: 信任背书（认证、合作伙伴、用户评价、数据指标）
- experience: 用户体验（FAQ、售后、退换政策）
- access: 获取方式（官网、社交媒体、联系方式、电商链接）
- content: 内容资产（最新新闻、公告、博客 — 每条必须有来源 URL）
- perception: 品牌感知（品牌调性、目标受众、使用场景）
- decision_factors: 决策因子（购买决策关键因素、感知风险）
- vitality: 品牌活力（最新动态、产品发布、增长信号）
- campaigns: 品牌活动（进行中/近期/即将到来的活动 — 每条必须有来源 URL）

  输出严格的 JSON，格式如下：
{{
  "scores": {{"identity": 8, "offerings": 3, ...所有11个维度}},
  "overall_score": 6.5,
  "gaps": [
    {{"dimension": "offerings", "missing": "缺少具体产品列表和价格信息", "action": "search", "query": "{brand_name} TOP产品 价格"}},
    {{"dimension": "offerings", "missing": "官网产品页未抓取", "action": "crawl", "target": "/products"}},
    {{"dimension": "trust", "missing": "缺少合作伙伴和投资方信息", "action": "deep_search", "query": "{brand_name} partners investors"}},
    {{"dimension": "vitality", "missing": "缺少最新动态", "action": "explore", "target_type": "news"}},
    ...更多gap
  ],
  "is_sufficient": false
}}

注意：
- action 有四种: "search"（单引擎搜索）、"deep_search"（双引擎搜索+自动抓取）、"crawl"（抓取指定已知路径）、"explore"（主动探索官网结构）
- search: 当需要外部信息补充时使用，query 必须是具体可执行的搜索词
- deep_search: 同时用 metaso + tavily 双引擎搜索，适用于搜索过但结果不够的情况；搜索结果中有具体URL时会自动抓取页面完整内容
- crawl: 当需要抓取特定已知路径时使用，target 是 URL 路径（如 /products）或完整 URL
- explore: 当某维度完全空缺且官网可能有对应页面时使用，target_type 可以是: products, news, about, partners, faq, blog
- overall_score >= 7 且 核心5维度(identity, offerings, differentiation, trust, access)都 >= 5 才算 is_sufficient: true
- gaps 数组最多 8 条（优先补最重要的缺口）"""

    result = chat_json(
        prompt, system="你是品牌知识库质量审查员。输出严格 JSON。", max_tokens=3000
    )

    if "scores" not in result:
        result["scores"] = {}
    if "gaps" not in result:
        result["gaps"] = []
    if "is_sufficient" not in result:
        overall = result.get("overall_score", 0)
        scores = result.get("scores", {})
        core_dims = ["identity", "offerings", "differentiation", "trust", "access"]
        core_ok = all(scores.get(d, 0) >= 5 for d in core_dims)
        result["is_sufficient"] = overall >= 7 and core_ok
    if "overall_score" not in result:
        scores = result.get("scores", {})
        result["overall_score"] = sum(scores.values()) / max(len(scores), 1)

    return result
