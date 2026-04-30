"""
Brand2Context v2 原型 — Goal-Driven Brand Researcher Agent

设计思路（学 Anthropic Claude / Hermes / OpenClaw / Manus）：
- 单一 Agent 自主循环：think → act (tool_call) → observe
- 9 层结构化 prompt（学 Hermes）
- LLM 是指挥官，工具是手脚（不再硬编码规则）
- 必须用工具行动（学 Hermes 名言："describe planned actions" 不行，必须真调用）
- 每个维度需要证据 source_url 才算可信

工具集（5 个）：
  1. crawl_page(url)              抓单页正文
  2. search_web(query, engine)    Tavily/Metaso 全网搜
  3. explore_links(url, intent)   抓首页提链接，LLM 选最相关
  4. read_evidence()              查看当前证据池摘要
  5. write_dimension(dim, data)   把某维度结构化数据写入最终结果

入口：
    python -m brand2context.v2.researcher --url https://nike.com --name Nike --category 运动品牌

输出：output/v2/<brand>_v2.json + 详细 trace 日志
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any
from urllib.parse import urlparse

# 复用现有底层工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from brand2context.llm import chat_json
from brand2context.crawler import _convert_page, _extract_internal_links
from brand2context.web_searcher import _search_tavily, _search_metaso, _is_china_brand
from brand2context.templates import DIMENSION_TEMPLATES
from brand2context.config import OUTPUT_DIR

# ======================================================================
# 常量
# ======================================================================

DIMENSIONS = [
    "identity", "offerings", "differentiation", "trust",
    "access", "content", "perception", "decision_factors", "vitality", "campaigns",
]

DIMENSION_DESC_CN = {
    "identity": "品牌身份：使命/愿景/价值观/创始人/历史",
    "offerings": "产品/服务列表：每条 SKU 含 name/category/price_range",
    "differentiation": "差异化优势：核心技术/专利/独特卖点",
    "trust": "信任背书：合作伙伴/认证/媒体报道/奖项",
    "access": "渠道入口：联系方式/门店/下载链接",
    "content": "内容资产：最新新闻/博客文章（含日期+url）",
    "perception": "外部感知：媒体评价/社交舆情/品牌形象关键词",
    "decision_factors": "决策因素：用户购买时关注的维度+本品牌评分",
    "vitality": "活力指标：最新产品发布/最新活动+日期",
    "campaigns": "营销活动：进行中+近期 campaign（含 name/type/date）",
}

MAX_ROUNDS = 15            # 最多决策轮数
MAX_TOOL_CALLS_PER_ROUND = 1  # 每轮 1 个工具调用，便于 trace
PAGE_CONTENT_PREVIEW = 800    # 工具结果回写时的预览长度
TIMEOUT_SECONDS = 600


# ======================================================================
# 证据池：所有抓回来的数据都存这里
# ======================================================================

class EvidencePool:
    """收集和管理 agent 所有抓回来的证据。"""

    def __init__(self):
        self.pages: dict[str, dict] = {}       # url -> {title, content, fetched_at}
        self.searches: list[dict] = []          # [{query, engine, results}]
        self.notes: list[str] = []              # agent 的中间笔记

    def add_page(self, url: str, title: str, content: str):
        self.pages[url] = {
            "title": title,
            "content": content,
            "fetched_at": time.time(),
            "length": len(content),
        }

    def add_search(self, query: str, engine: str, results: list[dict]):
        self.searches.append({
            "query": query, "engine": engine, "results": results,
            "fetched_at": time.time(),
        })

    def summary_for_agent(self) -> str:
        """给 agent 看的简洁摘要（不含全文），让它知道手上有什么。"""
        lines = []
        if self.pages:
            lines.append("已抓取页面：")
            for url, p in list(self.pages.items())[:30]:
                lines.append(f"  - [{p['length']}字] {p['title'][:40]} :: {url}")
        if self.searches:
            lines.append("\n已搜索：")
            for s in self.searches[-10:]:
                top_titles = [r.get("title", "")[:40] for r in s["results"][:3]]
                lines.append(f"  - [{s['engine']}] \"{s['query']}\" → {top_titles}")
        if self.notes:
            lines.append("\nAgent 中间笔记：")
            for n in self.notes[-5:]:
                lines.append(f"  • {n}")
        return "\n".join(lines) if lines else "（暂无证据）"

    def context_for_dimension(self, dimension: str, max_chars: int = 8000) -> str:
        """抽取该维度可能相关的全文上下文，用于最终 structure。"""
        chunks = []
        # 简单：把所有页面内容 + 搜索结果都塞进去（按重要性截断）
        for url, p in self.pages.items():
            chunks.append(f"--- PAGE {url} ({p['title']}) ---\n{p['content']}\n")
        for s in self.searches:
            chunks.append(f"--- SEARCH [{s['engine']}] \"{s['query']}\" ---")
            for r in s.get("results", [])[:5]:
                chunks.append(f"• {r.get('title','')} ({r.get('url','')}): {r.get('content','')[:400]}")
        combined = "\n".join(chunks)
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n[...截断...]"
        return combined


# ======================================================================
# 工具实现
# ======================================================================

def tool_crawl_page(url: str, evidence: EvidencePool) -> dict:
    """抓单个页面。"""
    if url in evidence.pages:
        return {"status": "cached", "url": url, "length": evidence.pages[url]["length"]}
    page = _convert_page(url)
    if not page:
        return {"status": "failed", "url": url, "error": "could not fetch"}
    evidence.add_page(page["url"], page.get("title", url), page["content"])
    preview = page["content"][:PAGE_CONTENT_PREVIEW]
    return {
        "status": "ok",
        "url": page["url"],
        "title": page.get("title", ""),
        "content_length": len(page["content"]),
        "preview": preview,
    }


def _do_search(engine: str, query: str) -> dict:
    if engine == "metaso":
        return _search_metaso(query, size=5)
    if engine == "tavily":
        return _search_tavily(query, max_results=5)
    raise ValueError(f"unknown engine: {engine}")


def tool_search_web(query: str, engine: str, evidence: EvidencePool, is_china: bool) -> dict:
    """全网搜（engine: tavily / metaso / auto）。任何引擎返回空或报错时自动 fallback 到另一个。"""
    # Tavily 额度耗尽期间强制 metaso 优先
    primary = engine if engine in ("metaso", "tavily") else "metaso"
    fallback = "tavily" if primary == "metaso" else "metaso"
    tried = []

    for eng in [primary, fallback]:
        try:
            results = _do_search(eng, query)
            res_list = results.get("results", []) or []
            tried.append({"engine": eng, "count": len(res_list)})
            if res_list:
                evidence.add_search(query, eng, res_list)
                return {
                    "status": "ok",
                    "engine": eng,
                    "query": query,
                    "fallback_used": eng != primary,
                    "tried": tried,
                    "answer": (results.get("answer") or "")[:500],
                    "top_results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""),
                         "snippet": r.get("content", "")[:200]}
                        for r in res_list[:5]
                    ],
                }
        except Exception as e:
            tried.append({"engine": eng, "error": str(e)[:100]})

    return {"status": "failed", "query": query, "tried": tried,
            "error": "两个搜索引擎都不可用或返回空结果"}


def tool_explore_links(url: str, intent: str, evidence: EvidencePool) -> dict:
    """抓首页 → 提取内链 → 让 LLM 根据 intent 选最相关的 5-10 个。"""
    if url in evidence.pages:
        homepage = {"url": url, "content": evidence.pages[url]["content"]}
    else:
        homepage = _convert_page(url)
        if not homepage:
            return {"status": "failed", "error": "homepage fetch failed"}
        evidence.add_page(homepage["url"], homepage.get("title", url), homepage["content"])

    links = _extract_internal_links(url, homepage["content"])
    if not links:
        return {"status": "ok", "links": [], "message": "no internal links found"}

    # LLM 选最相关的（不再死关键词匹配）
    select_prompt = f"""从以下内链中，选出最可能包含「{intent}」内容的 5-10 个 URL。

URL 列表（前 50 条）：
{json.dumps(links[:50], ensure_ascii=False, indent=2)}

请输出 JSON 数组，仅含选中的 URL 字符串："""
    try:
        result = chat_json(select_prompt, system="你是网站结构分析专家。",
                           max_tokens=1500, temperature=0.1)
        if isinstance(result, dict) and "urls" in result:
            selected = [u for u in result["urls"] if isinstance(u, str)]
        elif isinstance(result, list):
            selected = [u for u in result if isinstance(u, str)]
        else:
            selected = []
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    return {
        "status": "ok",
        "intent": intent,
        "total_links": len(links),
        "selected_count": len(selected),
        "selected_urls": selected[:10],
    }


def tool_read_page(url: str, evidence: EvidencePool) -> dict:
    """读取证据池中某 URL 已抓取的全文（最多 4000 字）。"""
    if url not in evidence.pages:
        return {"status": "not_in_pool", "url": url,
                "hint": "该 URL 还没抓，先用 crawl_page"}
    p = evidence.pages[url]
    content = p["content"]
    return {
        "status": "ok",
        "url": url,
        "title": p["title"],
        "full_length": p["length"],
        "content": content[:4000] + ("\n[...截断...]" if p["length"] > 4000 else ""),
    }


def tool_finalize_dimension(dimension: str, evidence: EvidencePool, brand_name: str, brand_url: str) -> dict:
    """对该维度做最终结构化抽取（用模板 + 上下文）。"""
    if dimension not in DIMENSION_TEMPLATES:
        return {"status": "failed", "error": f"unknown dimension: {dimension}"}

    template = DIMENSION_TEMPLATES[dimension]
    context = evidence.context_for_dimension(dimension)

    if len(context) < 100:
        return {
            "status": "insufficient_evidence",
            "dimension": dimension,
            "message": f"证据池中关于 {dimension} 的内容太少（{len(context)}字），请先用其他工具收集证据。",
        }

    prompt = f"""请根据以下证据，填充「{dimension}」维度的 JSON 模板。

## 模板：
{json.dumps(template, ensure_ascii=False, indent=2)}

## 维度说明：
{DIMENSION_DESC_CN.get(dimension, "")}

## 品牌：
{brand_name} ({brand_url})

## 证据：
{context}

## 规则：
1. 保持字段名和结构不变，只填值
2. 凡有具体信息的字段，必须附带 source_url（如果证据来自某 URL）
3. 数组字段：找到几条就填几条，没必要凑数
4. 推断的内容前加 [推断] 前缀
5. 完全找不到的留空字符串 ""

请直接输出填充后的 JSON："""
    try:
        result = chat_json(prompt,
                           system="你是品牌信息抽取专家，必须基于证据填充字段，不准编造。",
                           max_tokens=4000, temperature=0.2)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    # 质量门槛：填充字段太少 → 返回 insufficient 让 agent 继续找
    def _count_filled(o):
        if isinstance(o, str): return 1 if o.strip() else 0
        if isinstance(o, list): return sum(_count_filled(x) for x in o)
        if isinstance(o, dict): return sum(_count_filled(v) for v in o.values())
        return 1 if o is not None else 0
    filled = _count_filled(result)
    min_required = {"identity": 6, "offerings": 5, "differentiation": 4,
                    "trust": 3, "campaigns": 3, "perception": 3}
    threshold = min_required.get(dimension, 2)
    if filled < threshold:
        return {
            "status": "insufficient_evidence",
            "dimension": dimension,
            "filled": filled,
            "threshold": threshold,
            "message": f"抽取出来只有 {filled} 个非空字段（需 ≥ {threshold}）。请继续用 search_web/crawl_page 补充证据后重试。",
            "draft_data": result,
        }
    return {"status": "ok", "dimension": dimension, "data": result, "filled": filled}


# ======================================================================
# Agent Prompt（9 层结构 - 学 Hermes）
# ======================================================================

def build_agent_prompt(
    brand_name: str,
    brand_url: str,
    category: str,
    is_china: bool,
    completed_dims: list[str],
    pending_dims: list[str],
    current_dim: str,
    evidence: EvidencePool,
    round_num: int,
) -> tuple[str, str]:
    """返回 (system_prompt, user_prompt)。"""

    # ---- L1-L3 缓存层（不变）：身份 + 工具 + 维度规范 ----
    system = f"""# L1 身份
你是 BrandResearcher Agent，专门为品牌构建 11 维度知识库。

# L2 工作原则
- 你必须用工具行动，不准描述"我准备做什么"。
- 每一轮你只输出 1 个工具调用（JSON 格式）。
- 你看到的证据池是真实抓回来的数据，不在池里就是没有，不要凭想象编造。
- 完成一个维度前，必须保证证据池里有该维度相关的真实页面或搜索结果。

# L3 可用工具（严格 JSON 调用）
1. crawl_page         {{"tool": "crawl_page", "args": {{"url": "https://..."}}}}
   → 抓单页正文，写入证据池。
2. search_web         {{"tool": "search_web", "args": {{"query": "...", "engine": "auto|tavily|metaso"}}}}
   → 全网搜，结果写入证据池。
3. explore_links      {{"tool": "explore_links", "args": {{"url": "https://...", "intent": "products|news|about|..."}}}}
   → 抓首页+提链接+LLM 选 5-10 个最相关 URL（不会自动抓，你拿到 URL 后自己用 crawl_page 抓）。
4. read_page          {{"tool": "read_page", "args": {{"url": "https://..."}}}}
   → 读取已抓页面的全文（最多 4000 字）。仅在你需要看具体内容判断质量时用。
5. finalize_dimension {{"tool": "finalize_dimension", "args": {{"dimension": "offerings"}}}}
   → 对该维度做最终抽取。**会自动用证据池全部数据**，不需要你提前 read。

# L4 11 维度规范
{json.dumps(DIMENSION_DESC_CN, ensure_ascii=False, indent=2)}

# L5 输出格式（严格）
你每一轮只能输出一个 JSON 对象，结构：
{{
  "thought": "本轮我要做什么，为什么（1-2 句话）",
  "tool_call": {{"tool": "xxx", "args": {{...}}}}
}}
"""

    # ---- L6-L9 动态层：当前任务 + 证据 + 进度 + 时间 ----
    user = f"""# L6 当前研究目标
品牌：{brand_name}
官网：{brand_url}
品类：{category}
语言：{'中文（国内品牌）' if is_china else '英文（国际品牌）'}

# L7 进度
轮次：第 {round_num}/{MAX_ROUNDS} 轮
已完成维度（{len(completed_dims)}/11）：{completed_dims}
待完成维度（{len(pending_dims)}/11）：{pending_dims}
当前聚焦维度：**{current_dim}** — {DIMENSION_DESC_CN.get(current_dim, '')}

# L8 证据池摘要
{evidence.summary_for_agent()}

# L9 决策提示
- 证据池里**只要有 1-2 个**关于「{current_dim}」的相关页面或搜索结果，就**立即调用 finalize_dimension**。
- finalize_dimension 会自动用全部证据做抽取，**不需要你手动 read_page 后再 finalize**。
- 只有在证据池**完全为空**或都不相关时，才用 crawl_page / search_web / explore_links 去拿新数据。
- 警告：禁止重复调用同一工具相同参数（会被强制中断）。
- 国内品牌搜索用 metaso，国际品牌用 tavily。

请输出本轮的 JSON 决策："""
    return system, user


# ======================================================================
# 主循环
# ======================================================================

def run_researcher(brand_url: str, brand_name: str, category: str,
                   max_rounds: int = MAX_ROUNDS, verbose: bool = True) -> dict:
    """主入口：跑一个品牌的完整 v2 流程。"""
    is_china = _is_china_brand(brand_url, brand_name)
    evidence = EvidencePool()
    final_knowledge: dict[str, Any] = {
        "brand_name": brand_name,
        "brand_url": brand_url,
        "category": category,
        "schema_version": "v2.0",
    }
    completed_dims: list[str] = []
    pending_dims = list(DIMENSIONS)
    trace: list[dict] = []

    start_time = time.time()
    round_num = 0
    current_dim = pending_dims[0]

    print(f"\n🚀 BrandResearcher v2 启动")
    print(f"   品牌：{brand_name} | 品类：{category}")
    print(f"   官网：{brand_url}")
    print(f"   语言：{'中文' if is_china else '英文'}\n")

    while round_num < max_rounds and pending_dims:
        if time.time() - start_time > TIMEOUT_SECONDS:
            print(f"⏱️  超时退出（{TIMEOUT_SECONDS}s）")
            break

        round_num += 1
        current_dim = pending_dims[0]
        print(f"\n━━━━ Round {round_num} | 聚焦: {current_dim} ━━━━")

        # 让 LLM 决策下一步
        system, user = build_agent_prompt(
            brand_name, brand_url, category, is_china,
            completed_dims, pending_dims, current_dim, evidence, round_num,
        )

        try:
            decision = chat_json(user, system=system, max_tokens=1500, temperature=0.1)
        except Exception as e:
            print(f"   ⚠️ LLM 决策失败：{e}")
            trace.append({"round": round_num, "error": f"decision failed: {e}"})
            break

        thought = decision.get("thought", "(无思考)")
        tool_call = decision.get("tool_call", {})
        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {}) or {}

        print(f"   💭 {thought}")
        print(f"   🔧 {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:120]})")

        # 执行工具
        try:
            if tool_name == "crawl_page":
                tool_result = tool_crawl_page(tool_args.get("url", ""), evidence)
            elif tool_name == "search_web":
                tool_result = tool_search_web(
                    tool_args.get("query", ""),
                    tool_args.get("engine", "auto"),
                    evidence, is_china,
                )
            elif tool_name == "explore_links":
                tool_result = tool_explore_links(
                    tool_args.get("url", brand_url),
                    tool_args.get("intent", current_dim),
                    evidence,
                )
            elif tool_name == "read_page":
                tool_result = tool_read_page(tool_args.get("url", ""), evidence)
            elif tool_name == "read_evidence":  # 兼容旧名
                tool_result = {"status": "deprecated",
                               "message": "read_evidence 已弃用。证据摘要已在 prompt 里。如需读全文请用 read_page，否则直接 finalize_dimension。"}
            elif tool_name == "finalize_dimension":
                dim = tool_args.get("dimension", current_dim)
                tool_result = tool_finalize_dimension(dim, evidence, brand_name, brand_url)
                if tool_result.get("status") == "ok":
                    final_knowledge[dim] = tool_result["data"]
                    if dim in pending_dims:
                        pending_dims.remove(dim)
                    if dim not in completed_dims:
                        completed_dims.append(dim)
                    print(f"   ✅ 维度 {dim} 已完成（填充 {tool_result.get('filled','?')} | 剩余 {len(pending_dims)}）")
                elif tool_result.get("status") == "insufficient_evidence":
                    print(f"   ⚠️  {dim} 证据不足（填充 {tool_result.get('filled')}），要求继续补充")
            else:
                tool_result = {"status": "failed", "error": f"unknown tool: {tool_name}"}
        except Exception as e:
            tool_result = {"status": "failed", "error": str(e)}

        # 简短日志
        rs = tool_result.get("status", "?")
        if rs == "ok":
            extra = ""
            if tool_name == "crawl_page":
                extra = f" → {tool_result.get('content_length', 0)}字"
            elif tool_name == "search_web":
                extra = f" → {len(tool_result.get('top_results', []))}条结果"
            elif tool_name == "explore_links":
                extra = f" → 选出 {tool_result.get('selected_count', 0)} 个 URL"
            print(f"   📦 {rs}{extra}")
        else:
            print(f"   ⚠️ {rs}: {tool_result.get('error', tool_result.get('message', ''))[:120]}")

        trace.append({
            "round": round_num, "current_dim": current_dim,
            "thought": thought, "tool": tool_name, "args": tool_args,
            "result_status": rs,
        })

        # 防卡死：连续 3 次同样 (tool, args) 调用 → 强制 finalize 跳维
        recent = trace[-3:]
        if len(recent) == 3 and all(
            t.get("tool") == tool_name
            and json.dumps(t.get("args", {}), sort_keys=True) == json.dumps(tool_args, sort_keys=True)
            for t in recent
        ):
            print(f"   🚨 检测到死循环（{tool_name} ×3），强制 finalize {current_dim}")
            r = tool_finalize_dimension(current_dim, evidence, brand_name, brand_url)
            if r.get("status") == "ok":
                final_knowledge[current_dim] = r["data"]
            else:
                final_knowledge[current_dim] = dict(DIMENSION_TEMPLATES.get(current_dim, {}))
            if current_dim in pending_dims:
                pending_dims.remove(current_dim)
            completed_dims.append(current_dim)

    # 兜底：剩下的维度强制 finalize
    if pending_dims:
        print(f"\n🔄 兜底：强制 finalize 剩余 {len(pending_dims)} 个维度")
        for dim in list(pending_dims):
            r = tool_finalize_dimension(dim, evidence, brand_name, brand_url)
            if r.get("status") == "ok":
                final_knowledge[dim] = r["data"]
            else:
                final_knowledge[dim] = dict(DIMENSION_TEMPLATES.get(dim, {}))
            completed_dims.append(dim)
            pending_dims.remove(dim)

    # 输出
    elapsed = time.time() - start_time
    final_knowledge["_meta"] = {
        "rounds_used": round_num,
        "elapsed_seconds": round(elapsed, 1),
        "evidence_pages": len(evidence.pages),
        "evidence_searches": len(evidence.searches),
        "completed_dims": completed_dims,
    }

    out_dir = OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    safe_name = brand_name.lower().replace(" ", "-")
    out_file = os.path.join(out_dir, f"{safe_name}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_knowledge, f, ensure_ascii=False, indent=2)
    trace_dir = os.path.join(out_dir, "traces")
    os.makedirs(trace_dir, exist_ok=True)
    trace_file = os.path.join(trace_dir, f"{safe_name}_trace.json")
    with open(trace_file, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成 | 用时 {elapsed:.1f}s | 轮次 {round_num} | 抓页 {len(evidence.pages)} | 搜 {len(evidence.searches)}")
    print(f"   📄 输出：{out_file}")
    print(f"   📋 trace：{trace_file}")
    return final_knowledge


# ======================================================================
# CLI
# ======================================================================

def main():
    ap = argparse.ArgumentParser(description="Brand2Context v2 prototype")
    ap.add_argument("--url", required=True, help="brand homepage URL")
    ap.add_argument("--name", required=True, help="brand name")
    ap.add_argument("--category", default="未分类", help="brand category")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    args = ap.parse_args()
    run_researcher(args.url, args.name, args.category, max_rounds=args.max_rounds)


if __name__ == "__main__":
    main()
