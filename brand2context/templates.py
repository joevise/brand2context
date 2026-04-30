"""Dimension templates and validation for structured LLM output."""

DIMENSION_TEMPLATES = {
    "identity": {
        "name": "",
        "legal_name": "",
        "founded": "",
        "headquarters": "",
        "tagline": "",
        "mission": "",
        "vision": "",
        "values": [],
        "positioning": "",
        "category": "",
        "sub_categories": [],
        "brand_story": "",
        "founder": "",
        "scale": "",
    },
    "offerings": {
        "items": [
            {
                "name": "",
                "category": "",
                "description": "",
                "key_features": [],
                "specs": [],
                "price_range": "",
                "currency": "",
                "target_audience": "",
                "use_cases": [],
                "is_flagship": False,
                "launch_date": "",
                "status": "active",
                "source_url": "",
            }
        ]
    },
    "differentiation": {
        "unique_selling_points": [],
        "competitive_advantages": [],
        "technology_highlights": [],
        "patents_or_certifications": [],
        "awards": [],
        "comparison_notes": "",
    },
    "trust": {
        "certifications": [],
        "partnerships": [],
        "media_coverage": [],
        "investor_backed": "",
        "user_stats": [],
        "testimonials": [],
    },
    "access": {
        "official_website": "",
        "online_stores": [],
        "offline_presence": "",
        "contact": {"email": "", "phone": "", "address": ""},
        "social_media": [],
        "app": "",
    },
    "content": {
        "latest_news": [],
        "blog_posts": [],
        "key_announcements": [],
        "brand_guidelines_public": "",
    },
    "perception": {
        "personality_traits": [],
        "brand_tone": "",
        "price_positioning": "",
        "price_benchmark": "",
        "primary_audience": {"demographics": "", "psychographics": "", "geography": ""},
        "anti_audience": "",
        "category_association": "",
        "usage_occasions": [],
    },
    "decision_factors": {
        "category_key_factors": [],
        "perceived_risks": [],
        "switching_cost": "",
        "trial_barrier": "",
    },
    "vitality": {
        "content_frequency": "",
        "last_product_launch": "",
        "last_campaign": "",
        "growth_signal": "",
        "community_size": "",
        "nps_or_satisfaction": "",
        "repeat_purchase_rate": "",
        "market_position": "",
        "industry_role": "",
    },
    "campaigns": {"ongoing": [], "recent": [], "upcoming": [], "annual_events": []},
}


def validate_and_fix(dimension: str, data: dict) -> dict:
    """强制校验并修正LLM输出，确保符合模板结构。

    规则：
    1. 缺失字段 → 补默认值
    2. 类型不对 → 强转（string→[string]包一层, dict→[dict]包一层, etc）
    3. 多余字段（如type/properties/description） → 删除（schema污染）
    4. offerings 特殊处理：统一到 items 数组
    """
    template = DIMENSION_TEMPLATES.get(dimension, {})
    if not template:
        return data
    if not isinstance(data, dict):
        return dict(template)

    schema_keys = {
        "type",
        "description",
        "properties",
        "required",
        "additionalProperties",
    }

    if "properties" in data and "type" in data:
        props = data["properties"]
        extracted = {}
        for k, v in props.items():
            if isinstance(v, dict) and "value" in v:
                extracted[k] = v["value"]
            elif isinstance(v, dict) and "type" in v and len(v) <= 3:
                extracted[k] = ""
            else:
                extracted[k] = v
        data = extracted

    for sk in schema_keys:
        data.pop(sk, None)
    data.pop("schema_version", None)

    result = {}
    for field, default_val in template.items():
        val = data.get(field, default_val)

        if isinstance(default_val, list):
            if isinstance(val, dict):
                val = [val]
            elif isinstance(val, str):
                val = [val] if val else []
            elif not isinstance(val, list):
                val = []
        elif isinstance(default_val, str):
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val) if val else ""
            elif isinstance(val, dict):
                val = str(val)
            elif not isinstance(val, str):
                val = str(val) if val else ""
        elif isinstance(default_val, dict):
            if not isinstance(val, dict):
                val = dict(default_val)

        result[field] = val

    if dimension == "offerings":
        items = result.get("items", [])
        if not items and "offerings" in data:
            items = data["offerings"]
            if isinstance(items, dict):
                items = [items]
        result["items"] = items if isinstance(items, list) else []

    # content: 如果LLM把新闻字段打平到顶层，收集到latest_news里
    if dimension == "content":
        if not result.get("latest_news") and ("title" in data or "summary" in data):
            news_item = {}
            for k in ("title", "date", "summary", "url", "source_url"):
                if k in data and data[k]:
                    news_item[k] = data[k]
            if news_item:
                result["latest_news"] = [news_item]

    # decision_factors: 字符串数组 → 结构化对象数组
    if dimension == "decision_factors":
        for field in ["category_key_factors", "perceived_risks"]:
            items = result.get(field, [])
            if items and isinstance(items[0], str):
                if field == "category_key_factors":
                    result[field] = [
                        {"factor": s, "brand_score": "", "evidence": ""} for s in items
                    ]
                elif field == "perceived_risks":
                    result[field] = [{"risk": s, "mitigation": ""} for s in items]

    return result
