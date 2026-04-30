"""v1 vs v2 横向对比脚本。"""
import json, os, time, subprocess, sys

BRANDS = [
    {"name": "Nike",       "url": "https://www.nike.com",       "category": "运动品牌", "slug": "nike"},
    {"name": "lululemon",  "url": "https://www.lululemon.com",  "category": "运动服饰", "slug": "lululemon"},
    {"name": "小米",       "url": "https://www.mi.com",         "category": "科技品牌", "slug": "小米"},
    {"name": "茶颜悦色",   "url": "https://www.chayanyuese.com", "category": "新茶饮",   "slug": "茶颜悦色"},
]

DIMENSIONS = ["identity","offerings","differentiation","trust","experience",
              "access","content","perception","decision_factors","vitality","campaigns"]

OUTPUT_DIR = "output"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def count_filled(o):
    if isinstance(o, str): return 1 if o.strip() else 0
    if isinstance(o, list): return sum(count_filled(x) for x in o)
    if isinstance(o, dict): return sum(count_filled(v) for v in o.values())
    return 1 if o is not None else 0

def run_v1(brand):
    """跑 v1 pipeline。"""
    print(f"\n[v1] {brand['name']} 启动")
    t0 = time.time()
    env = os.environ.copy()
    env["TAVILY_API_KEY"] = "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"
    env["METASO_API_KEY"] = "mk-DA5C2447D54689CD7757A0C4AB162CA3"
    try:
        r = subprocess.run(
            ["python3", "-m", "brand2context", brand["url"]],
            capture_output=True, text=True, timeout=900, env=env,
        )
        elapsed = time.time() - t0
        # v1 输出 output/<slug>.json
        path = os.path.join(OUTPUT_DIR, f"{brand['slug']}.json")
        if os.path.exists(path):
            return {"path": path, "elapsed": elapsed, "ok": True}
        return {"ok": False, "elapsed": elapsed, "stderr": r.stderr[-500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed": 900, "stderr": "timeout"}

def run_v2(brand):
    """跑 v2 prototype。"""
    print(f"\n[v2] {brand['name']} 启动")
    t0 = time.time()
    env = os.environ.copy()
    env["TAVILY_API_KEY"] = "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"
    env["METASO_API_KEY"] = "mk-DA5C2447D54689CD7757A0C4AB162CA3"
    try:
        r = subprocess.run(
            ["python3", "-m", "brand2context.v2.researcher",
             "--url", brand["url"], "--name", brand["name"],
             "--category", brand["category"], "--max-rounds", "30"],
            capture_output=True, text=True, timeout=900, env=env,
        )
        elapsed = time.time() - t0
        slug = brand["name"].lower().replace(" ", "-")
        path = os.path.join(OUTPUT_DIR, "v2", f"{slug}_v2.json")
        if os.path.exists(path):
            return {"path": path, "elapsed": elapsed, "ok": True, "stdout_tail": r.stdout[-2000:]}
        return {"ok": False, "elapsed": elapsed, "stderr": r.stderr[-500:], "stdout_tail": r.stdout[-1500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed": 900, "stderr": "timeout"}

def analyze(path):
    if not path or not os.path.exists(path):
        return None
    d = json.load(open(path))
    out = {"_meta": d.get("_meta", {})}
    total = 0
    for dim in DIMENSIONS:
        f = count_filled(d.get(dim, {}))
        out[dim] = f
        total += f
    out["TOTAL"] = total
    return out

def main():
    results = {}
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for b in BRANDS:
        if only and b["slug"] not in only and b["name"] not in only:
            continue
        results[b["name"]] = {"brand": b}
        # v2 first (we already have nike/lulu)
        v2_path = os.path.join(OUTPUT_DIR, "v2", f"{b['name'].lower().replace(' ', '-')}_v2.json")
        if os.path.exists(v2_path) and "--rerun-v2" not in sys.argv:
            print(f"[v2] {b['name']} 已有结果，跳过重跑")
            results[b["name"]]["v2"] = {"ok": True, "path": v2_path, "elapsed": None, "cached": True}
        else:
            results[b["name"]]["v2"] = run_v2(b)

        v1_path = os.path.join(OUTPUT_DIR, f"{b['slug']}.json")
        if os.path.exists(v1_path) and "--rerun-v1" not in sys.argv:
            print(f"[v1] {b['name']} 已有结果，跳过重跑")
            results[b["name"]]["v1"] = {"ok": True, "path": v1_path, "elapsed": None, "cached": True}
        else:
            results[b["name"]]["v1"] = run_v1(b)

    # 分析
    print("\n" + "="*100)
    print(f"{'品牌':<14} {'版本':<4} {'用时':>6} {'identity':>9} {'offerings':>10} {'diff':>5} {'trust':>6} {'exp':>5} {'access':>7} {'content':>8} {'perc':>5} {'decision':>9} {'vit':>5} {'camp':>5} {'TOTAL':>6}")
    print("="*100)
    summary = []
    for name, r in results.items():
        for ver in ["v1", "v2"]:
            res = r.get(ver, {})
            if not res.get("ok"):
                print(f"{name:<14} {ver:<4} FAILED: {res.get('stderr','')[:60]}")
                continue
            stats = analyze(res.get("path"))
            if not stats: continue
            elapsed = res.get("elapsed")
            elapsed_str = f"{elapsed:.0f}s" if elapsed else "cache"
            row = f"{name:<14} {ver:<4} {elapsed_str:>6} "
            for dim in DIMENSIONS:
                key = dim[:8] if dim != "decision_factors" else "decision"
                row += f"{stats[dim]:>{len(key)+2}} "
            row += f"{stats['TOTAL']:>6}"
            print(row)
            summary.append({"brand": name, "version": ver,
                            "elapsed": elapsed, "stats": stats})

    out_file = "output/v2/comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n📊 汇总：{out_file}")

if __name__ == "__main__":
    main()
