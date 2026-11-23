# -*- coding: utf-8 -*-
"""Builds data/ledger_fy<YEAR>.json from PaymentAccuracy.gov's FY<YEAR>_Dataset.xlsx.

    python3 make_ledger.py 2026 2026-11-23

All sums are FraudBad's, read straight from the official file. No figure is estimated."""
import collections, json, os, re, sys
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    return " ".join(str(s).split())


def build(fy, pulled):
    path = os.path.join(HERE, "data", "pa", f"FY{fy}_Dataset.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["All Program Results "].iter_rows(values_only=True))
    H = [norm(h) if h else h for h in rows[0]]
    R = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        d = dict(zip(H, r))
        R.append(d)
    years = collections.defaultdict(lambda: {"amount_m": 0.0, "outlays_m": 0.0, "programs": 0})
    for d in R:
        y = years[int(d["Fiscal Year"])]
        y["amount_m"] += d["Improper Payment and Unknown Payment Amount ($M)"] or 0
        y["outlays_m"] += d["Outlays Amount ($M)"] or 0
        y["programs"] += 1
    prev = {(d["Agency"].strip(), norm(d["Program Name"])): d["Improper Payment and Unknown Payment Rate"]
            for d in R if int(d["Fiscal Year"]) == fy - 1}
    progs = []
    for d in R:
        if int(d["Fiscal Year"]) != fy:
            continue
        a, p = d["Agency"].strip(), norm(d["Program Name"])
        progs.append({"agency": a, "program": p, "outlays_m": d["Outlays Amount ($M)"], "improper_m": d["Improper Payment Amount ($M)"],
                      "unknown_m": d["Unknown Payment Amount ($M)"], "total_m": d["Improper Payment and Unknown Payment Amount ($M)"] or 0,
                      "rate": d["Improper Payment and Unknown Payment Rate"], "over_m": d["Total Overpayments Amount ($M)"],
                      "prev_rate": prev.get((a, p))})
    progs.sort(key=lambda p: -p["total_m"])
    rc = list(wb["Improper Payment Root Causes"].iter_rows(values_only=True))
    RH = [re.sub(r"\s*\(\$M\)$", "", str(h)).strip() if h else "" for h in rc[0]]
    causes = collections.defaultdict(float)
    for r in rc[1:]:
        if not r or not r[0] or not isinstance(r[3], (int, float)) or int(r[3]) != fy:
            continue
        for i in range(4, min(len(RH), len(r))):
            if isinstance(r[i], (int, float)):
                causes[RH[i]] += r[i]
    rec_rows = list(wb["Rate and Amt of Recovery"].iter_rows(values_only=True))
    RRH = [str(h).strip() if h else "" for h in rec_rows[0]]
    rec = collections.defaultdict(lambda: {"identified_m": 0.0, "recovered_m": 0.0})
    for r in rec_rows[1:]:
        # skip the sheet's own "Grand Total" row: adding it to the agency rows would count every dollar twice
        if not r or not r[0] or "total" in str(r[0]).lower():
            continue
        for i, h in enumerate(RRH):
            m = re.match(r"(\d{4}) Overpayment Amount Identified", h)
            if m and i + 1 < len(r) and isinstance(r[i], (int, float)) and isinstance(r[i + 1], (int, float)):
                rec[int(m.group(1))]["identified_m"] += r[i]
                rec[int(m.group(1))]["recovered_m"] += r[i + 1]
    ct = list(wb["Compliance Trend Table"].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(ct) if r and r[0] == "Agency")
    CH = ct[hi]
    col = max(i for i, h in enumerate(CH) if isinstance(h, int) and any(
        r and len(r) > i and r[i] in ("Compliant", "Non-compliant", "Non-Compliant") for r in ct[hi + 1:]))
    cyear = CH[col]
    agencies, rated, nonc = 0, 0, []
    for r in ct[hi + 1:]:
        if not r or not r[0] or "%" in str(r[0]):
            continue
        agencies += 1
        v = r[col] if len(r) > col else None
        if v in ("Compliant", "Non-compliant", "Non-Compliant"):
            rated += 1
            if v.lower() == "non-compliant":
                nonc.append(str(r[0]).strip())
    yrs = {str(k): {"amount_m": round(v["amount_m"], 2), "outlays_m": round(v["outlays_m"], 2), "programs": v["programs"]} for k, v in sorted(years.items())}
    return {
        "source": f"https://paymentaccuracy.gov/assets/files/FY{fy}_Dataset.xlsx",
        "page": "https://www.paymentaccuracy.gov/resources",
        "pulled": pulled,
        "years": yrs,
        f"programs_{fy}": progs,
        f"root_causes_{fy}_m": {k: round(v, 2) for k, v in causes.items() if v},
        "recovery_m": {str(k): {"identified_m": round(v["identified_m"], 2), "recovered_m": round(v["recovered_m"], 2)} for k, v in sorted(rec.items()) if k >= 2013},
        f"compliance_fy{cyear}": {"noncompliant": sorted(nonc, key=str.lower), "agencies": agencies, "rated": rated},
        "cumulative_m": round(sum(v["amount_m"] for v in years.values()), 2),
        f"cum_through_{fy - 1}_m": round(sum(v["amount_m"] for k, v in years.items() if k < fy), 2),
    }


if __name__ == "__main__":
    fy, pulled = int(sys.argv[1]), sys.argv[2]
    out = build(fy, pulled)
    dest = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "data", f"ledger_fy{fy}.json")
    json.dump(out, open(dest, "w"), indent=1)
    print("wrote", dest)
