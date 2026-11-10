"""Step 2 of 3.6: compact candidate list per state from the extracted single-audit text.
For every 'questioned cost(s)' followed by a dollar amount: amount, finding number (nearest 20YY-NNN before it),
program (nearest Assistance Listing number before it), and a short snippet. Current-year = finding number from the
audit's own year. Output: candidates.json. Usage: python3 -I candidates.py [ST ...] (prints top 4 per state)"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALN = {"93.778": "Medicaid", "93.767": "CHIP", "10.551": "SNAP", "10.561": "SNAP administration", "93.558": "TANF",
       "84.425": "COVID-19 school relief (ESSER)", "21.027": "COVID-19 State and Local Fiscal Recovery Funds",
       "21.029": "COVID-19 Capital Projects Fund", "17.225": "Unemployment insurance", "93.575": "Child care (CCDF)",
       "93.596": "Child care (CCDF)", "93.489": "Child care (CCDF)", "10.557": "WIC", "20.205": "Highway construction",
       "84.010": "Title I schools", "84.027": "Special education (IDEA)", "93.323": "COVID-19 epidemiology and lab grants",
       "93.268": "Immunization grants", "14.228": "Community development block grants", "97.036": "FEMA disaster aid",
       "21.023": "Emergency rental assistance", "93.959": "Substance use block grant", "10.555": "School lunch",
       "10.553": "School breakfast", "10.558": "Child and adult care food", "10.559": "Summer food service",
       "93.568": "Home energy assistance (LIHEAP)", "93.659": "Adoption assistance", "93.658": "Foster care",
       "84.126": "Vocational rehabilitation", "93.917": "HIV care", "66.458": "Clean water revolving fund",
       "66.468": "Drinking water revolving fund", "93.788": "Opioid response grants", "17.258": "WIOA adult",
       "17.259": "WIOA youth", "17.278": "WIOA dislocated worker", "84.367": "Teacher quality (Title II)",
       "93.044": "Older Americans Act", "93.045": "Older Americans Act meals", "11.035": "Broadband (BEAD)",
       "21.026": "Homeowner assistance fund", "93.391": "COVID-19 health disparities grants", "97.067": "Homeland security grants",
       "20.507": "Transit formula grants", "20.106": "Airport improvement", "93.667": "Social services block grant"}
AMT = re.compile(r"\$\s?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,})(?:\.[0-9]{2})?")


def cands(st, v):
    t = open(os.path.join(HERE, "raw", "fac", f"{st}.txt"), encoding="utf-8", errors="ignore").read()
    flat = re.sub(r"[ \t]+", " ", t)
    fy = v["fy_end"][:4]
    out = []
    for m in re.finditer(r"questioned\s+costs?", flat, re.I):
        win = flat[m.end(): m.end() + int(os.environ.get("WIN", "200"))]
        a = AMT.search(win)
        if not a:
            continue
        amt = float(a.group(1).replace(",", ""))
        if amt < 1000 or "expended" in win[:a.start()].lower():
            continue
        before = flat[max(0, m.start() - 8000): m.start()]
        refs = re.findall(r"\b(20[12][0-9]-[0-9]{3,4})\b", before)
        after_refs = re.findall(r"\b(20[12][0-9]-[0-9]{3,4})\b", flat[m.end(): m.end() + 600])
        ref = refs[-1] if refs else (after_refs[0] if after_refs else "")
        alns = re.findall(r"\b(\d{2}\.\d{3})\b", before[-5000:])
        prog = next((ALN[x] for x in reversed(alns) if x in ALN), "")
        aln = alns[-1] if alns else ""
        prior = (ref and not ref.startswith(fy)) or bool(re.search(r"prior audit finding number|summary schedule of prior", flat[max(0, m.start() - 1500): m.start()], re.I))
        likely = bool(re.search(r"likely|project", flat[m.start(): m.end() + 400], re.I))
        out.append({"amount": amt, "ref": ref, "aln": aln, "program": prog, "prior": bool(prior), "likely": likely,
                    "pos": m.start(), "snip": flat[m.start(): m.end() + 230].replace("\n", " ")})
    best = {}
    for c in out:  # dedupe by (ref, amount)
        k = (c["ref"], round(c["amount"]))
        best.setdefault(k, c)
    return sorted(best.values(), key=lambda c: (c["prior"], -c["amount"]))


if __name__ == "__main__":
    q = json.load(open(os.path.join(HERE, "questioned.json")))
    sts = sys.argv[1:] or sorted(q)
    allc = {}
    for st in sts:
        if st not in q:
            continue
        c = cands(st, q[st])
        allc[st] = c
        cur = [x for x in c if not x["prior"]]
        print(f"===== {st} {q[st]['auditor'][:34]} FYE {q[st]['fy_end']} cur={len(cur)}")
        for x in cur[:4]:
            print(f"  ${x['amount']:,.0f} {x['ref']} {x['aln']} {x['program'][:28]} L={int(x['likely'])} | {x['snip'][:210]}")
    p = os.path.join(HERE, "candidates.json")
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(allc)
    json.dump(old, open(p, "w"), indent=1)
