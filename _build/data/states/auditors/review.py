"""Print the top current-year questioned costs per state for hand review. Usage: python3 -I review.py ST [ST ...] [--n 3] [--w 520]"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
n = int(args[args.index("--n") + 1]) if "--n" in args else 3
w = int(args[args.index("--w") + 1]) if "--w" in args else 520
sts = [a for a in args if re.fullmatch(r"[A-Z]{2}", a)]
q = json.load(open(os.path.join(HERE, "questioned.json")))
for st in sts:
    v = q.get(st)
    if not v:
        print("=====", st, "NO DATA")
        continue
    cur = [h for h in v["top"] if not h["prior"]]
    print(f"===== {st} | {v['auditor'][:45]} | FYE {v['fy_end']} | {v['n_hits']} amounts | {v['report_id']}")
    seen = set()
    for h in cur:
        key = (h["ref"], round(h["amount"]))
        if key in seen:
            continue
        seen.add(key)
        c = h["ctx"]
        i = c.lower().rfind("questioned cost", 0, len(c) - 250)
        print(f"-- ${h['amount']:,.0f} ref={h['ref']} likely={h['likely']}")
        print("   " + c[max(0, i - w): i + 260].replace("\n", " "))
        if len(seen) >= n:
            break
