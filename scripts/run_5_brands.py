"""跑 5 个品牌验证 v2 主系统。"""
import json, os, time, subprocess, sys

BRANDS = [
    {"name": "Nike",         "url": "https://www.nike.com",        "category": "运动品牌"},
    {"name": "lululemon",    "url": "https://www.lululemon.com",   "category": "运动服饰"},
    {"name": "小米",         "url": "https://www.mi.com",          "category": "科技品牌"},
    {"name": "Patagonia",    "url": "https://www.patagonia.com",   "category": "户外品牌"},
    {"name": "三顿半",       "url": "https://www.saturnbird.com",  "category": "新消费咖啡"},
]

DIMENSIONS = ["identity","offerings","differentiation","trust",
              "access","content","perception","decision_factors","vitality","campaigns"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def cf(o):
    if isinstance(o, str): return 1 if o.strip() else 0
    if isinstance(o, list): return sum(cf(x) for x in o)
    if isinstance(o, dict): return sum(cf(v) for v in o.values())
    return 1 if o is not None else 0

def run_one(b):
    print(f"\n{'='*60}\n[{b['name']}] 启动\n{'='*60}")
    t0 = time.time()
    env = os.environ.copy()
    env.setdefault("TAVILY_API_KEY", "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")
    env.setdefault("METASO_API_KEY", "mk-DA5C2447D54689CD7757A0C4AB162CA3")
    env["PYTHONUNBUFFERED"] = "1"
    try:
        r = subprocess.run(
            ["python3", "-u", "-m", "brand2context",
             b["url"], "--name", b["name"], "--category", b["category"],
             "--max-rounds", "30"],
            capture_output=True, text=True, timeout=900, env=env,
        )
        elapsed = time.time() - t0
        slug = b["name"].lower().replace(" ", "-")
        path = os.path.join("output", f"{slug}.json")
        if os.path.exists(path):
            return {"ok": True, "path": path, "elapsed": elapsed}
        return {"ok": False, "elapsed": elapsed, "stderr": r.stderr[-800:], "stdout_tail": r.stdout[-1500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed": 900, "stderr": "timeout"}

def main():
    results = []
    for b in BRANDS:
        r = run_one(b)
        results.append({"brand": b["name"], **r})
        if r.get("ok"):
            d = json.load(open(r["path"]))
            counts = {dim: cf(d.get(dim, {})) for dim in DIMENSIONS}
            total = sum(counts.values())
            print(f"   ✅ TOTAL={total} | {counts}")
            results[-1]["counts"] = counts
            results[-1]["total"] = total
        else:
            print(f"   ❌ FAILED: {r.get('stderr','')[:200]}")

    print("\n" + "="*100)
    print(f"{'品牌':<12} {'用时':>5}s {'总分':>4}  " + "  ".join(f"{d[:6]:>6}" for d in DIMENSIONS))
    print("="*100)
    for r in results:
        if not r.get("ok"):
            print(f"{r['brand']:<12} ❌ {r.get('stderr','')[:80]}")
            continue
        c = r["counts"]
        line = f"{r['brand']:<12} {r['elapsed']:>5.0f}  {r['total']:>4}  "
        line += "  ".join(f"{c[d]:>6}" for d in DIMENSIONS)
        print(line)
    with open("output/run5_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n📊 汇总：output/run5_summary.json")

if __name__ == "__main__":
    main()
