"""Plan item 3.6, step 1: for each state government's FY2025 single audit (Federal Audit Clearinghouse), download the
report PDF, extract text, and list every questioned-cost amount with its surrounding text, largest first.
Input: fac_big_2025.json (FAC /general rows). Output: raw/fac/<STATE>.txt (text) + questioned.json.
Usage: python3 -I fac_questioned.py [STATE ...]"""
import json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw", "fac")
os.makedirs(RAW, exist_ok=True)
NAME = re.compile(r"\b(state|commonwealth) of\b|government of the district", re.I)
NOT = re.compile(r"universit|housing|authority|transit|mortgage", re.I)
AMT = re.compile(r"\$\s?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{2})?")


def state_rows():
    rows = json.load(open(os.path.join(HERE, "fac_big_2025.json")))
    best = {}
    for r in rows:
        if not NAME.search(r["auditee_name"].strip()) or NOT.search(r["auditee_name"]):
            continue
        if r["auditee_state"] not in best or r["total_amount_expended"] > best[r["auditee_state"]]["total_amount_expended"]:
            best[r["auditee_state"]] = r
    for r in json.load(open(os.path.join(HERE, "fac_extra.json"))):  # states with no FY2025 statewide audit filed yet
        best.setdefault(r["auditee_state"], r)
    return best


def text_for(st, r):
    txt = os.path.join(RAW, f"{st}.txt")
    if os.path.exists(txt) and os.path.getsize(txt) > 1000:
        return open(txt, encoding="utf-8", errors="ignore").read()
    pdf = os.path.join(RAW, f"{st}.pdf")
    url = f"https://app.fac.gov/dissemination/report/pdf/{r['report_id']}"
    req = urllib.request.Request(url, headers={"User-Agent": "FraudBad research (+https://fraudbad.com/about)"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(pdf, "wb") as f:
        while True:
            b = resp.read(1 << 20)
            if not b:
                break
            f.write(b)
    subprocess.run(["pdftotext", "-layout", pdf, txt], check=False)
    os.remove(pdf)
    return open(txt, encoding="utf-8", errors="ignore").read()


def questioned(t):
    flat = re.sub(r"[ \t]+", " ", t)
    hits = []
    for m in re.finditer(r"questioned\s+costs?", flat, re.I):
        win = flat[m.end(): m.end() + 160]
        a = AMT.search(win)
        if not a:
            continue
        # skip "$X threshold"/"exceed $25,000" boilerplate
        pre = flat[max(0, m.start() - 120): m.start()].lower()
        if "greater than" in pre or "in excess of" in pre or "exceed" in win[:a.start()].lower():
            continue
        v = float(a.group(1).replace(",", ""))
        if v < 1000:
            continue
        before = flat[max(0, m.start() - 4000): m.start()]
        refs = re.findall(r"\b(20[12][0-9]-[0-9]{3,4})\b", before)
        prior = bool(re.search(r"prior[- ]year finding|schedule of prior audit findings", before[-2500:], re.I))
        likely = "likely" in win[:a.end() + 40].lower() or "project" in flat[m.end(): m.end() + 400].lower()
        hits.append({"amount": v, "ref": refs[-1] if refs else "", "prior": prior, "likely": likely,
                     "ctx": flat[max(0, m.start() - 900): m.end() + 300]})
    hits.sort(key=lambda h: (h["prior"], -h["amount"]))
    return hits


if __name__ == "__main__":
    rows = state_rows()
    want = [s.upper() for s in sys.argv[1:]] or sorted(rows)
    out_p = os.path.join(HERE, "questioned.json")
    out = json.load(open(out_p)) if os.path.exists(out_p) else {}
    for st in want:
        r = rows.get(st)
        if not r:
            print(st, "no FY2025 state single audit in list")
            continue
        try:
            t = text_for(st, r)
        except Exception as ex:  # noqa: BLE001
            print(st, "FAIL", ex)
            continue
        h = questioned(t)
        out[st] = {"report_id": r["report_id"], "auditee": r["auditee_name"], "auditor": r["auditor_firm_name"],
                   "fy_end": r["fy_end_date"], "accepted": r["fac_accepted_date"], "expended": r["total_amount_expended"],
                   "pdf": f"https://app.fac.gov/dissemination/report/pdf/{r['report_id']}",
                   "summary": f"https://app.fac.gov/dissemination/summary/{r['report_id']}",
                   "n_hits": len(h), "top": h[:6]}
        print(st, r["auditor_firm_name"][:40], len(t) // 1000, "k chars,", len(h), "amounts, max", f"${h[0]['amount']:,.0f}" if h else "-", flush=True)
        json.dump(out, open(out_p, "w"), indent=1)
