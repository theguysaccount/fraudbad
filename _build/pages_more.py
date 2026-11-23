# -*- coding: utf-8 -*-
"""Phase 1 and Phase 3 pages: about, corrections, open data, embeds, feed, and one page for every
program, agency and fiscal year in the government's own improper-payment file.

Every number here is read from data/pa/FY2025_Dataset.xlsx (PaymentAccuracy.gov) or from the case files.
Sums and ranks are ours and are labelled that way on the page."""
import collections, csv, io, json, os, re, zipfile
import xml.etree.ElementTree as ET
try:
    import openpyxl
except ImportError:
    openpyxl = None

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "data", "pa", "FY2025_Dataset.xlsx")
MIN_YEARS = 5  # a program gets its own page once it has this many years of results

NAMES = {
    "CNCS": "AmeriCorps (Corporation for National and Community Service)", "CPSC": "Consumer Product Safety Commission",
    "DHS": "Department of Homeland Security", "DOC": "Department of Commerce", "DOI": "Department of the Interior",
    "DOJ": "Department of Justice", "DOL": "Department of Labor", "DOT": "Department of Transportation",
    "DOW": "Department of Defense (War)", "ED": "Department of Education", "EPA": "Environmental Protection Agency",
    "FCC": "Federal Communications Commission", "GSA": "General Services Administration",
    "HHS": "Department of Health and Human Services", "HUD": "Department of Housing and Urban Development",
    "NASA": "NASA", "NSF": "National Science Foundation", "OPM": "Office of Personnel Management",
    "RRB": "Railroad Retirement Board", "SBA": "Small Business Administration", "SSA": "Social Security Administration",
    "STATE": "Department of State", "Treasury": "Department of the Treasury", "USAGM (BBG)": "U.S. Agency for Global Media",
    "USAID": "U.S. Agency for International Development", "USDA": "Department of Agriculture", "VA": "Department of Veterans Affairs",
}
RC_PLAIN = {
    "Failure to Access Data/Information Needed": "Data existed and was accessible, but nobody checked it",
    "Data/Information Needed Does Not Exist": "The data needed to check it didn't exist",
    "Inability to Access the Data/Information": "Data existed, but the agency couldn't get it",
    "Insufficient Documentation to Determine": "Not enough paperwork to tell either way",
    "Insufficient or Lacking Documentation From States": "States didn't send enough paperwork",
    "Insufficient or Lacking Documentation From Vendor or provider": "Vendors or providers didn't send enough paperwork",
    "Insufficient or Lacking Documentation for Eligibility from Applicants": "Applicants didn't prove they were eligible",
    "Insufficient or Lacking Documentation From  Scenario Not Previously Specified": "Missing paperwork, other",
    "Technically Improper Payments (Made for correct amount but failed to meet all regulatory and/or statutory requirements)": "Right amount, but the rules weren't followed",
}


def slug(s, n=72):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("’", "").replace("&", " and ")).strip("-")
    return s[:n].rsplit("-", 1)[0] if len(s) > n else s


def program_parts(p):
    """(sub-agency prefix or '', program's own name)"""
    if " - " in p:
        head, _, tail = p.rpartition(" - ")
        head, tail = head.strip(), tail.strip()
        acr = re.search(r"\(([A-Z]{2,6})\)$", tail)
        if acr and tail.startswith("U.S. "):  # 'Commercial Pay - U.S. Army Corps of Engineers (USACE)': the program is the head
            return tail, f"{head} ({acr.group(1)})"
        return head, tail
    return "", p


def pname(B, p, href=None):
    pre, core = program_parts(p)
    name = f'<a href="{href}">{B.e(core)}</a>' if href else B.e(core)
    return f'<b>{name}</b>' + (f'<span class="ag">{B.e(pre)}</span>' if pre else "")


def program_core(p):
    """The program's own name without the sub-agency prefix: 'Centers for ... (CMS) - Medicaid' -> 'Medicaid'."""
    return p.split(" - ")[-1].strip() if " - " in p else p


def agency_name(a):
    return NAMES.get(a, a)


def agency_slug(a):
    return slug(a.replace("(BBG)", ""))


# ------------------------------------------------------------------ load the official file once
_D = {}


def _col_idx(ref):
    m = re.match(r"([A-Z]+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _read_xlsx_stdlib(path):
    """Pure-stdlib fallback reader for FY2025_Dataset.xlsx when openpyxl is not installed."""
    ns_m = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{{{ns_m}}}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns_m}}}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rmap = {el.attrib["Id"]: el.attrib["Target"] for el in rels}
        out = {}
        for sh in wb.findall(f".//{{{ns_m}}}sheet"):
            name = sh.attrib["name"]
            target = "xl/" + rmap[sh.attrib[f"{{{ns_r}}}id"]].lstrip("/")
            if target.startswith("xl/xl/"):
                target = target[3:]
            sroot = ET.fromstring(z.read(target))
            rows = []
            for row in sroot.findall(f".//{{{ns_m}}}sheetData/{{{ns_m}}}row"):
                rnum = int(row.attrib.get("r", len(rows) + 1))
                while len(rows) < rnum - 1:
                    rows.append((None,))
                vals = {}
                max_c = -1
                for c in row.findall(f"{{{ns_m}}}c"):
                    ci = _col_idx(c.attrib["r"])
                    if ci > max_c:
                        max_c = ci
                    t = c.attrib.get("t")
                    v_el = c.find(f"{{{ns_m}}}v")
                    if t == "s" and v_el is not None:
                        val = shared[int(v_el.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(f"{{{ns_m}}}t"))
                    elif t == "b" and v_el is not None:
                        val = v_el.text == "1"
                    elif t in ("str", "e") and v_el is not None:
                        val = v_el.text
                    elif v_el is not None and v_el.text is not None:
                        raw = v_el.text
                        try:
                            val = int(raw) if raw.lstrip("-").isdigit() else float(raw)
                        except ValueError:
                            val = raw
                    else:
                        val = None
                    vals[ci] = val
                rows.append(tuple(vals.get(i) for i in range(max_c + 1)) if max_c >= 0 else (None,))
            out[name] = rows
        return out


def _sheet_rows(path, wb, sheet_name):
    if wb is not None:
        return list(wb[sheet_name].iter_rows(values_only=True))
    return _read_xlsx_stdlib(path)[sheet_name]


def data():
    if _D:
        return _D
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True) if openpyxl is not None else None
    sheets = None if wb is not None else _read_xlsx_stdlib(XLSX)
    rows = list(wb["All Program Results "].iter_rows(values_only=True)) if wb is not None else sheets["All Program Results "]
    H = rows[0]
    R = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        d = dict(zip(H, r))
        R.append({"agency": d["Agency"].strip(), "program": " ".join(str(d["Program Name"]).split()), "fy": int(d["Fiscal Year"]),
                  "outlays": d["Outlays Amount ($M)"], "improper": d["Improper Payment Amount ($M)"],
                  "unknown": d["Unknown Payment Amount  ($M)"], "total": d["Improper Payment and Unknown Payment Amount ($M)"] or 0,
                  "rate": d["Improper Payment and Unknown Payment Rate"], "over": d["Total Overpayments Amount ($M)"],
                  "under": d["Underpayment Amount ($M)"]})
    rc_rows = list(wb["Improper Payment Root Causes"].iter_rows(values_only=True)) if wb is not None else sheets["Improper Payment Root Causes"]
    RH = rc_rows[0]
    RC = collections.defaultdict(lambda: collections.defaultdict(float))  # (agency, program, fy) -> cause -> $M
    for r in rc_rows[1:]:
        if not r or not r[0]:
            continue
        key = (r[0].strip(), " ".join(str(r[1]).split()), int(r[3]))
        for i in range(4, min(len(RH), len(r))):
            if isinstance(r[i], (int, float)):
                RC[key][RH[i].strip()] += r[i]
    rec_rows = list(wb["Rate and Amt of Recovery"].iter_rows(values_only=True)) if wb is not None else sheets["Rate and Amt of Recovery"]
    RRH = [str(h).strip() if h else "" for h in rec_rows[0]]
    REC = collections.defaultdict(dict)  # agency -> fy -> (identified, recovered)
    for r in rec_rows[1:]:
        if not r or not r[0]:
            continue
        a = str(r[0]).strip()
        for i, h in enumerate(RRH):
            m = re.match(r"(\d{4}) Overpayment Amount Identified", h)
            if m and i + 1 < len(r) and isinstance(r[i], (int, float)) and isinstance(r[i + 1], (int, float)):
                REC[a][int(m.group(1))] = (r[i], r[i + 1])
    ct = list(wb["Compliance Trend Table"].iter_rows(values_only=True)) if wb is not None else sheets["Compliance Trend Table"]
    CH = ct[1]
    COMP = {}
    for r in ct[2:]:
        if r and r[0] and isinstance(r[0], str) and not str(r[0]).replace(".", "").isdigit():
            COMP[r[0].strip()] = {int(CH[i]): r[i] for i in range(1, min(len(CH), len(r))) if isinstance(CH[i], int) and r[i] in ("Compliant", "Non-Compliant")}
    by_prog = collections.defaultdict(list)
    for r in R:
        by_prog[(r["agency"], r["program"])].append(r)
    for v in by_prog.values():
        v.sort(key=lambda r: r["fy"])
    years = sorted({r["fy"] for r in R})
    _D.update(R=R, RC=RC, REC=REC, COMP=COMP, by_prog=by_prog, years=years)
    # page addresses
    used = set()
    links = {}
    eligible = [(a, p) for (a, p), rs in sorted(by_prog.items()) if len(rs) >= MIN_YEARS]
    core_count = collections.Counter(slug(f"{agency_slug(a)}-{program_core(p)}") for a, p in eligible)
    for (a, p), rs in sorted(by_prog.items()):
        if len(rs) < MIN_YEARS:
            continue
        s = slug(f"{agency_slug(a)}-{program_core(p)}")
        if core_count[s] > 1:
            s = slug(f"{agency_slug(a)}-{p}")
        while s in used:
            s += "-2"
        used.add(s)
        links[(a, p)] = f"/program/{s}"
    _D["links"] = links
    _D["agencies"] = sorted({r["agency"] for r in R})
    return _D


def fmt(m, digits=None):
    """$ millions -> words-sized money."""
    if m is None:
        return "—"
    if abs(m) >= 1000:
        return f"${m/1000:,.{1 if digits is None else digits}f}B"
    if abs(m) >= 1:
        return f"${m:,.0f}M"
    return "<$1M" if m > 0 else "$0"


def pct(x, d=1):
    return "—" if x is None else f"{x*100:.{d}f}%"


def year_bars(series, B, hi_years=(), link=None):
    """series: [(fy, $M)] -> the ledger's bar chart markup (bars link to year pages)."""
    top = max((v for _, v in series), default=0) or 1
    n = len(series)
    cells, xl = [], []
    keep = {series[0][0], series[-1][0], max(series, key=lambda t: t[1])[0]} | set(hi_years)
    for fy, v in series:
        tag = "a" if link else "div"
        href = f' href="/year/{fy}"' if link else ""
        lab = f"<b>{fmt(v, 0) if v >= 1000 else fmt(v)}</b>" if fy in keep else ""
        cells.append(f'<{tag} class="y{" hi" if fy in keep else ""}"{href} style="--h:{v/top*100:.1f}%" title="FY{fy}: {fmt(v)}">{lab}</{tag}>')
        show = fy in keep or (n > 10 and fy % 5 == 0 and all(abs(fy - k) >= 3 for k in keep))
        xl.append(f'<span{" class=k" if show else ""}>{fy if fy in keep else str(fy)[2:]}</span>')
    style = f'style="grid-template-columns:repeat({n},minmax(0,1fr))"'
    return (f'<div class="yrs" {style} role="img" aria-label="Improper and unverifiable payments by fiscal year">{"".join(cells)}</div>'
            f'<div class="yrs-x" {style} aria-hidden="true">{"".join(xl)}</div>')


def src_line(B, ids):
    out = []
    for sid in ids:
        t, pub, date, url = B.S[sid]
        out.append(f'<li><span><a href="{B.e(url)}" rel="noopener">{B.e(t)}</a><span class="src">{B.e(pub)} · {B.e(date)}</span></span></li>')
    return f'<section class="sec" id="sources"><div class="wrap prose"><h2>Sources</h2><ol class="sources">{"".join(out)}</ol></div></section>'


def page(B, path, active, title, desc, og, kicker, h1, lede, body, ld=None, breadcrumbs=None):
    url_path = "/" + (path[:-10] if path.endswith("/index.html") else path[:-5])
    bc_items = list(breadcrumbs) if breadcrumbs else [("Home", "/"), (re.sub(r"<[^>]+>", "", str(h1)).strip(), url_path)]
    if not bc_items or bc_items[0][1] != "/":
        bc_items = [("Home", "/")] + bc_items
    if bc_items[-1][1] != url_path:
        bc_items.append((re.sub(r"<[^>]+>", "", str(h1)).strip(), url_path))
    extra_ld = [B.ORG_LD, B.breadcrumb_ld(*bc_items)] + (ld or [])
    head = B.head(title, desc, url_path, og, extra_ld)
    hero = f"""<section class="page-hero"><div class="wrap">
<p class="kicker" style="color:#ff4438">{kicker}</p><h1 class="h1-mid">{h1}</h1><p class="lede">{lede}</p></div></section>"""
    B.write(path, head + B.header(active) + '<main id="main">' + hero + body + "</main>" + B.cta() + B.footer())
    if path.endswith(".html") and not path.startswith("embed/"):
        u = "/" + (path[:-10] if path.endswith("/index.html") else path[:-5])
        B.EXTRA_URLS.append(u)


def crumbs(*items):
    parts = [f'<a href="{h}">{t}</a>' if h else f"<span>{t}</span>" for t, h in items]
    return f'<nav class="crumbs" aria-label="Breadcrumb">{" / ".join(parts)}</nav>'


# Verified bi-directional cross-links between FraudBad cases and official state/agency/program ledgers.
CASE_LINKS = {
    "federal-fraud-estimate": {"hubs": [("/hard-fraud", "All hard fraud cases"), ("/ledger", "Federal improper payment ledger"), ("/answers/how-much-fraud-is-in-the-federal-government", "How much federal fraud?")]},
    "improper-payments-2025": {"hubs": [("/year/2025", "FY2025 improper payments"), ("/ledger", "All 64 FY2025 programs"), ("/agencies", "All 27 federal agencies")]},
    "pandemic-unemployment-fraud": {"agencies": ["dol"], "programs": ["dol-federal-state-unemployment-insurance"], "hubs": [("/states", "State UI improper-payment rates"), ("/answers/which-states-have-the-highest-unemployment-fraud-rates", "State UI fraud rankings")]},
    "ppp-eidl-loan-fraud": {"agencies": ["sba"], "programs": ["sba-disaster-assistance-loans", "sba-7-a-business-loans"], "hubs": [("/answers/how-much-pandemic-money-was-lost-to-fraud", "Pandemic relief fraud summary")]},
    "employee-retention-credit": {"agencies": ["treasury"], "hubs": [("/answers/how-much-pandemic-money-was-lost-to-fraud", "Pandemic relief fraud summary")]},
    "operation-gold-rush": {"agencies": ["hhs", "doj"], "programs": ["hhs-medicare-fee-for-service-ffs"]},
    "health-care-fraud-takedown-2026": {"agencies": ["hhs", "doj"], "programs": ["hhs-medicare-fee-for-service-ffs", "hhs-medicaid"]},
    "medicare-advantage-overpayments": {"agencies": ["hhs"], "programs": ["hhs-medicare-advantage-part-c"]},
    "medicare-medicaid-no-receipts": {"agencies": ["hhs"], "programs": ["hhs-medicare-fee-for-service-ffs", "hhs-medicaid", "hhs-childrens-health-insurance-program-chip"]},
    "snap-payment-errors": {"agencies": ["usda"], "programs": ["usda-supplemental-nutrition-assistance-program"], "hubs": [("/states", "All 51 SNAP state error rates"), ("/answers/which-states-have-the-highest-snap-error-rates", "Highest SNAP error-rate states")]},
    "tax-credit-errors": {"agencies": ["treasury"], "programs": ["treasury-earned-income-tax-credit", "treasury-additional-child-tax-credit", "treasury-american-opportunity-tax-credit"]},
    "pentagon-failed-audits": {"agencies": ["dow"], "programs": ["dow-commercial-pay", "dow-military-pay", "dow-civilian-pay"]},
    "afghanistan-reconstruction": {"agencies": ["dow", "state", "usaid"]},
    "minnesota-medicaid-programs": {"states": ["MN"], "agencies": ["hhs"], "programs": ["hhs-medicaid"]},
    "feeding-our-future": {"states": ["MN"], "agencies": ["usda"], "programs": ["usda-national-school-lunch-program"]},
    "arizona-sober-living-fraud": {"states": ["AZ"], "agencies": ["hhs"], "programs": ["hhs-medicaid"]},
    "california-unemployment-fraud": {"states": ["CA"], "agencies": ["dol"], "programs": ["dol-federal-state-unemployment-insurance"]},
    "michigan-unemployment-fraud": {"states": ["MI"], "agencies": ["dol"], "programs": ["dol-federal-state-unemployment-insurance"]},
    "new-york-unemployment-overpayments": {"states": ["NY"], "agencies": ["dol"], "programs": ["dol-federal-state-unemployment-insurance"]},
    "washington-unemployment-theft": {"states": ["WA"], "agencies": ["dol"], "programs": ["dol-federal-state-unemployment-insurance"]},
    "mississippi-welfare-scandal": {"states": ["MS"], "agencies": ["hhs"]},
    "los-angeles-homelessness-spending": {"states": ["CA"], "agencies": ["hud"]},
    "los-angeles-hospice-fraud": {"states": ["CA"], "agencies": ["hhs"], "programs": ["hhs-medicare-fee-for-service-ffs"]},
    "improper-payments-since-2003": {"hubs": [("/ledger", "The full ledger"), ("/years", "FY2004–FY2025 by year"), ("/answers/how-much-money-has-the-government-paid-wrong", "Total paid wrong since 2004")]},
    "health-care-waste": {"agencies": ["hhs"], "programs": ["hhs-medicare-fee-for-service-ffs", "hhs-medicaid"]},
    "tax-gap": {"agencies": ["treasury"]},
    "weapons-cost-overruns": {"agencies": ["dow"]},
    "unfixed-gao-savings": {"hubs": [("/ledger", "Federal improper payment ledger"), ("/agencies", "All 27 federal agencies")]},
    "federal-it-legacy-systems": {"agencies": ["gsa"]},
    "contracts-with-no-description": {"hubs": [("/contracts", "Explore all 100 top contracts"), ("/answers/which-federal-contracts-have-no-description", "Contracts with no description")]},
    "data-existed-nobody-checked": {"hubs": [("/ledger#why", "FY2025 root causes"), ("/year/2025", "FY2025 improper payments"), ("/answers/which-federal-agencies-failed-payment-integrity-compliance", "Non-compliant agencies")]},
    "september-spending-rush": {"hubs": [("/contracts", "FY2026 top contracts"), ("/data", "Monthly contract CSV")]},
    "shuttered-venue-grants": {"agencies": ["sba"], "hubs": [("/answers/which-federal-programs-have-the-highest-error-rates", "Highest error-rate programs")]},
    "hud-rental-assistance-unverified": {"agencies": ["hud"], "programs": ["hud-housing-certificate-fund-and-tenant-based-rental-assistance", "hud-housing-for-persons-with-disability-section-811"]},
    "federal-debt-never-collected": {"agencies": ["treasury"], "hubs": [("/answers/how-much-improper-payment-money-is-recovered", "Overpayment recovery rates")]},
    "social-security-overpayments": {"agencies": ["ssa"], "programs": ["ssa-old-age-and-survivors-insurance-oasi", "ssa-supplemental-security-income-ssi"]},
    "snap-card-skimming": {"agencies": ["usda"], "programs": ["usda-supplemental-nutrition-assistance-program"], "hubs": [("/states", "SNAP error rates by state")]},
    "false-claims-act-2025": {"agencies": ["doj"], "programs": ["doj-law-enforcement"]},
    "sentinel-icbm-overrun": {"agencies": ["dow"]},
    "california-high-speed-rail": {"states": ["CA"], "agencies": ["dot"], "programs": ["dot-federal-transit-administration-capital-investment-grants"]},
    "honolulu-rail": {"states": ["HI"], "agencies": ["dot"], "programs": ["dot-federal-transit-administration-capital-investment-grants"]},
    "second-avenue-subway": {"states": ["NY"], "agencies": ["dot"], "programs": ["dot-federal-transit-administration-capital-investment-grants"]},
    "medicare-generic-drug-prices": {"agencies": ["hhs"], "programs": ["hhs-medicare-prescription-drug-benefit-part-d"]},
}

_STATE_NAMES = None


def _state_name_map():
    global _STATE_NAMES
    if _STATE_NAMES is None:
        us = json.load(open(os.path.join(HERE, "data", "states", "usaspending_states_fy2025.json")))["states"]
        _STATE_NAMES = {s["code"]: s["name"].replace("District Of Columbia", "District of Columbia") for s in us.values()}
    return _STATE_NAMES


def case_related_html(B, c):
    """Render verified cross-links from a case page to its matching state, agency, program and hub pages."""
    info = CASE_LINKS.get(c["slug"], {})
    D = data()
    prog_by_slug = {url[len("/program/"):]: (a, p) for (a, p), url in D["links"].items()}
    ag_by_slug = {agency_slug(a): a for a in D["agencies"]}
    snames = _state_name_map()
    pills = []
    pills.append((f"/hard-fraud" if c["type"] == "hard" else "/soft-fraud",
                  "Hard fraud cases" if c["type"] == "hard" else "Soft fraud hub"))
    for st in info.get("states", []):
        if st in snames:
            pills.append((f"/state/{st.lower()}", f"{snames[st]} state ledger"))
    for ag in info.get("agencies", []):
        if ag in ag_by_slug:
            pills.append((f"/agency/{ag}", f"{agency_name(ag_by_slug[ag])} ({ag_by_slug[ag]})"))
    for ps in info.get("programs", []):
        if ps in prog_by_slug:
            _, pname_ = prog_by_slug[ps]
            pills.append((f"/program/{ps}", f"{program_parts(pname_)[1]} ledger"))
    for href, label in info.get("hubs", []):
        pills.append((href, label))
    if not pills:
        return ""
    lis = "".join(f'<li><a href="{B.e(h)}">{B.e(lab)} →</a></li>' for h, lab in pills)
    return f'<section class="rel-records"><h2>Related official records</h2><p>Explore the underlying agency, state, and program datasets connected to this case.</p><ul class="rel-pills">{lis}</ul></section>'


def _cases_for_agency(B, a):
    aslg = agency_slug(a)
    by = {c["slug"]: c for c in B.ORDERED}
    return [by[s] for s, info in CASE_LINKS.items() if aslg in info.get("agencies", []) and s in by]


def _cases_for_program(B, prog_url):
    pslg = prog_url[len("/program/"):]
    by = {c["slug"]: c for c in B.ORDERED}
    return [by[s] for s, info in CASE_LINKS.items() if pslg in info.get("programs", []) and s in by]


# Concise SEO title overrides for long OMB program names (>70 chars even without brand)
PROGRAM_TITLE_OVERRIDES = {
    "dot-federal-highway-administration-highway-planning-and-construction": "DOT Highway Planning & Construction: Improper Payments | FraudBad",
    "dot-federal-transit-administration-capital-investment-grants": "FTA Capital Investment Grants: Improper Payments | FraudBad",
    "dot-federal-transit-administration-emergency-relief-program": "FTA Emergency Relief Program: Improper Payments | FraudBad",
    "dot-federal-aviation-administration-grants-in-aid-for-airports": "FAA Airport Grants-in-Aid: Improper Payments | FraudBad",
    "usda-wic-special-supplemental-nutrition-program-for-women-infants-and": "USDA WIC Program (Historic): Improper Payments | FraudBad",
    "usda-special-nutrition-program-for-women-infants-and-children-wic": "USDA WIC Nutrition Program: Improper Payments | FraudBad",
    "usda-commodity-credit-corporation-ccc-supplemental-revenue-assistance": "USDA CCC SURE Program: Improper Payments | FraudBad",
    "usda-commodity-credit-corporation-ccc-marketing-assistance-loan-mal": "USDA CCC Marketing Assistance Loan: Improper Payments | FraudBad",
    "usda-commodity-credit-corporation-ccc-livestock-forage-disaster-program": "USDA CCC Livestock Forage Program: Improper Payments | FraudBad",
    "usda-rma-federal-crop-insurance-corporation-fcic-program-fund": "USDA RMA Crop Insurance (FCIC): Improper Payments | FraudBad",
    "usda-rural-housing-service-rhs-multi-family-housing-rental-assistance": "USDA RHS Multi-Family Rental Aid: Improper Payments | FraudBad",
    "va-civilian-health-and-medical-program-of-the-va-champva": "VA CHAMPVA Program: Improper Payments | FraudBad",
    "hud-housing-certificate-fund-and-tenant-based-rental-assistance": "HUD Tenant-Based Rental Assistance: Improper Payments | FraudBad",
}


# ------------------------------------------------------------------ program pages
def build_programs(B):
    D = data()
    latest = max(D["years"])
    f25 = sorted([r for r in D["R"] if r["fy"] == latest], key=lambda r: -(r["total"] or 0))
    rank = {(r["agency"], r["program"]): i for i, r in enumerate(f25, 1)}
    for (a, p), url in D["links"].items():
        rs = D["by_prog"][(a, p)]
        last = rs[-1]
        total = sum(r["total"] or 0 for r in rs)
        rk = rank.get((a, p))
        if last["fy"] == latest:
            lede = (f"In fiscal {latest}, this program paid {fmt(last['total'])} wrong or without proof — {pct(last['rate'])} of "
                    f"{fmt(last['outlays'])} it paid out. That ranks #{rk} of {len(f25)} programs that reported.")
        else:
            lede = f"Its last reported year is fiscal {last['fy']}: {fmt(last['total'])} paid wrong or without proof, {pct(last['rate'])} of {fmt(last['outlays'])}."
        trs = "".join(
            f'<tr><td class="mono"><a href="/year/{r["fy"]}">FY{r["fy"]}</a></td><td class="num">{fmt(r["outlays"])}</td><td class="num">{fmt(r["total"])}</td>'
            f'<td class="mono hide-sm">{fmt(r["unknown"]) if r["unknown"] else "—"}</td><td class="mono">{pct(r["rate"])}</td></tr>' for r in reversed(rs))
        causes = D["RC"].get((a, p, last["fy"]))
        rc_html = ""
        if causes:
            tot = sum(causes.values()) or 1
            items = sorted(causes.items(), key=lambda kv: -kv[1])
            mx = items[0][1] or 1
            rc_html = (f'<h2>Why it happened, fiscal {last["fy"]}</h2><div class="bars-chart wide">' + "".join(
                f'<div class="bar-row"><span>{B.e(RC_PLAIN.get(k, k))}</span><div class="track"><div class="fill" style="--w:{v/mx*100:.1f}%"></div></div><b>{fmt(v)}</b></div>'
                for k, v in items if v > 0) + f'</div><p class="src">Root-cause categories are set by OMB and reported by {B.e(agency_name(a))}. Total {fmt(tot)}.</p>')
        comp = D["COMP"].get(a, {})
        c24 = comp.get(2024)
        comp_line = f"{B.e(agency_name(a))} was rated <b>{'out of compliance' if c24 == 'Non-Compliant' else 'compliant'}</b> with the payment-integrity law for fiscal 2024." if c24 else ""
        series = [(r["fy"], r["total"] or 0) for r in rs]
        rel_cases = _cases_for_program(B, url)
        rel_cases_html = (f'<section class="sec" style="background:var(--paper-2)"><div class="wrap"><h2>Related FraudBad cases</h2>'
                          f'<div class="grid" style="margin-top:22px">{"".join(B.card(c) for c in rel_cases)}</div></div></section>') if rel_cases else ""
        pre, core = program_parts(p)
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('Programs', '/programs'), (B.e(agency_name(a)), f'/agency/{agency_slug(a)}'), (B.e(core), None))}
<div class="big-grid">
<div class="big"><b>{fmt(total)}</b><span>paid wrong or without proof, FY{rs[0]['fy']}–FY{last['fy']} (our sum)</span></div>
<div class="big"><b>{pct(last['rate'])}</b><span>error rate in fiscal {last['fy']}</span></div>
<div class="big"><b>{len(rs)}</b><span>years of results on record</span></div>
</div>
<h2 style="margin-top:48px">Paid wrong, year by year</h2>{year_bars(series, B, link=True)}
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Year</th><th>Paid out</th><th>Wrong or unproven</th><th class="hide-sm">Of that, can't tell</th><th>Rate</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="src">"Can't tell" means the agency couldn't prove the payment right or wrong. All amounts are the agency's own estimates.</p>
</div></section>
<section class="sec"><div class="wrap prose">{rc_html}<p>{comp_line} <a href="/agency/{agency_slug(a)}">Every {B.e(a)} program →</a> · <a href="/programs">All {len(D['links'])} federal programs →</a></p>
<p class="src">Improper payments include mistakes and missing paperwork as well as fraud. This page shows how much, not why in any one case.</p></div></section>
{rel_cases_html}
{src_line(B, ['pa_data', 'pa_site'])}"""
        pslg = url[len("/program/"):]
        if pslg in PROGRAM_TITLE_OVERRIDES:
            title = [PROGRAM_TITLE_OVERRIDES[pslg]]
        else:
            title = [f"{p} ({a}): improper payments by year | FraudBad", f"{p}: improper payments by year | FraudBad", f"{core} ({a}): improper payments by year | FraudBad", f"{core}: improper payments by year | FraudBad", f"{core} improper payments | FraudBad"]
        # Concise, unique, non-truncated meta description (<= 165 chars)
        desc_full = f"{p}, {agency_name(a)}: {fmt(total)} paid wrong or without proof over {len(rs)} years of official results. Latest: {pct(last['rate'])} in fiscal {last['fy']}."
        desc_core = f"{core} ({a}): {fmt(total)} in improper and unproven payments over {len(rs)} fiscal years (FY{rs[0]['fy']}–FY{last['fy']}). Latest rate: {pct(last['rate'])} in FY{last['fy']}."
        desc_short = f"{core[:68].rsplit(' ', 1)[0]} ({a}): {fmt(total)} paid wrong across {len(rs)} years; FY{last['fy']} error rate {pct(last['rate'])}."
        desc = desc_full if len(desc_full) <= 165 else (desc_core if len(desc_core) <= 165 else desc_short)
        ds_ld = [{"@context": "https://schema.org", "@type": "Dataset",
                  "name": f"{core} ({a}) improper payments, FY{rs[0]['fy']}–FY{last['fy']}",
                  "description": desc, "url": B.SITE + url,
                  "creator": {"@type": "Organization", "name": agency_name(a)},
                  "isBasedOn": B.S["pa_data"][3], "temporalCoverage": f"{rs[0]['fy']}/{last['fy']}",
                  "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"}]
        page(B, url[1:] + ".html", "ledger", title, desc, "og-ledger.png",
             B.e(agency_name(a) + (" · " + pre if pre else "")), B.e(core), B.e(lede), body,
             ld=ds_ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), (agency_name(a), f"/agency/{agency_slug(a)}"), (core, url)])


# ------------------------------------------------------------------ agency pages
def build_agencies(B):
    D = data()
    latest = max(D["years"])
    for a in D["agencies"]:
        rs = [r for r in D["R"] if r["agency"] == a]
        by_y = collections.defaultdict(float)
        for r in rs:
            by_y[r["fy"]] += r["total"] or 0
        series = sorted(by_y.items())
        progs = sorted({(r["program"]) for r in rs})
        rows = []
        for p in progs:
            prs = D["by_prog"][(a, p)]
            l = prs[-1]
            name = pname(B, p, D["links"].get((a, p)))
            rows.append((l["fy"], l["total"] or 0, f'<tr><td>{name}</td><td class="mono">FY{l["fy"]}</td><td class="num">{fmt(l["total"])}</td><td class="mono hide-sm">{pct(l["rate"])}</td><td class="mono hide-sm">{len(prs)}</td></tr>'))
        rows.sort(key=lambda t: (-t[0], -t[1]))
        comp = D["COMP"].get(a, {})
        comp_cells = "".join(f'<span class="cmp {"bad" if v == "Non-Compliant" else "ok"}" title="FY{y}: {v}">{str(y)[2:]}</span>' for y, v in sorted(comp.items()))
        rec = D["REC"].get(a, {})
        rec_rows = "".join(f'<tr><td class="mono">FY{y}</td><td class="num">{fmt(i)}</td><td class="num">{fmt(g)}</td></tr>' for y, (i, g) in sorted(rec.items(), reverse=True) if i or g)
        total = sum(v for _, v in series)
        rel_cases = _cases_for_agency(B, a)
        rel_cases_html = (f'<section class="sec" style="background:var(--paper-2)"><div class="wrap"><h2>Major FraudBad cases involving {B.e(agency_name(a))}</h2>'
                          f'<div class="grid" style="margin-top:22px">{"".join(B.card(c) for c in rel_cases)}</div></div></section>') if rel_cases else ""
        lede = (f"{agency_name(a)} has reported {fmt(total)} in improper and unverifiable payments across {len(progs)} programs since fiscal {series[0][0]}, by our sum of its own reports."
                + (f" In fiscal {latest}: {fmt(by_y[latest])}." if latest in by_y else ""))
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('Agencies', '/agencies'), (B.e(agency_name(a)), None))}
<h2>Paid wrong, year by year</h2>{year_bars(series, B, link=True)}
<p class="src">All of {B.e(a)}'s reporting programs combined, each fiscal year. Bars link to that year. <a href="/agencies">Compare all {len(D['agencies'])} agencies →</a></p></div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>Every program it has reported</h2>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Program</th><th>Latest year</th><th>Wrong or unproven</th><th class="hide-sm">Rate</th><th class="hide-sm">Years reported</th></tr></thead><tbody>{''.join(r[2] for r in rows)}</tbody></table></div>
</div></section>
{rel_cases_html}
<section class="sec"><div class="wrap prose">
{f'<h2>Did it follow the payment-integrity law?</h2><p class="cmp-row">{comp_cells}</p><p class="src">Red = rated out of compliance by its inspector general that fiscal year. Green = compliant.</p>' if comp else ''}
{f'<h2>Overpayments flagged and recovered</h2><div class="tbl-wrap"><table class="tbl" style="min-width:0"><thead><tr><th>Year</th><th>Flagged to recover</th><th>Recovered</th></tr></thead><tbody>{rec_rows}</tbody></table></div>' if rec_rows else ''}
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
        clean_ag = re.sub(r" *\(.*?\)", "", agency_name(a))
        title = [f"{agency_name(a)}: every improper payment it has reported | FraudBad", f"{clean_ag}: every improper payment it reported | FraudBad", f"{clean_ag} improper payments | FraudBad"]
        desc_full = f"{agency_name(a)}: {fmt(total)} in improper and unverifiable payments since fiscal {series[0][0]}, program by program, from the government's own data."
        desc_short = f"{clean_ag} ({a}): {fmt(total)} in improper and unverifiable payments across {len(progs)} programs since FY{series[0][0]}, from OMB's official dataset."
        desc = desc_full if len(desc_full) <= 165 else desc_short
        ag_url = f"/agency/{agency_slug(a)}"
        ds_ld = [{"@context": "https://schema.org", "@type": "Dataset",
                  "name": f"{agency_name(a)} improper payments, FY{series[0][0]}–FY{series[-1][0]}",
                  "description": desc, "url": B.SITE + ag_url,
                  "creator": {"@type": "Organization", "name": agency_name(a)},
                  "isBasedOn": B.S["pa_data"][3], "temporalCoverage": f"{series[0][0]}/{series[-1][0]}",
                  "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"}]
        page(B, f"agency/{agency_slug(a)}.html", "ledger", title, desc, "og-ledger.png", "Agency", B.e(agency_name(a)), B.e(lede), body,
             ld=ds_ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), ("Agencies", "/agencies"), (agency_name(a), ag_url)])


# ------------------------------------------------------------------ year pages
def build_years(B):
    D = data()
    for fy in D["years"]:
        rs = sorted([r for r in D["R"] if r["fy"] == fy], key=lambda r: -(r["total"] or 0))
        tot = sum(r["total"] or 0 for r in rs)
        out = sum(r["outlays"] or 0 for r in rs)
        prev = [r for r in D["R"] if r["fy"] == fy - 1]
        ptot = sum(r["total"] or 0 for r in prev)
        chg = ""
        if prev:
            d = tot - ptot
            chg = f" That's {fmt(abs(d))} {'more' if d > 0 else 'less'} than fiscal {fy-1}."
        pmap = {(r["agency"], r["program"]): r for r in prev}
        movers = []
        for r in rs:
            pr = pmap.get((r["agency"], r["program"]))
            if pr:
                movers.append(((r["total"] or 0) - (pr["total"] or 0), r))
        up = sorted([m for m in movers if m[0] > 0], key=lambda t: -t[0])[:5]
        dn = sorted([m for m in movers if m[0] < 0], key=lambda t: t[0])[:5]

        def nm(r):
            k = (r["agency"], r["program"])
            core = program_parts(r["program"])[1]
            return f'<a href="{D["links"][k]}">{B.e(core)}</a>' if k in D["links"] else B.e(core)
        top = "".join(f'<tr><td class="rk">{i}</td><td><b>{nm(r)}</b><span class="ag"><a href="/agency/{agency_slug(r["agency"])}">{B.e(agency_name(r["agency"]))}</a></span></td><td class="num">{fmt(r["total"])}</td><td class="mono">{pct(r["rate"])}</td></tr>' for i, r in enumerate(rs, 1))
        mv = lambda L, sign: "".join(f'<li>{nm(r)}: {sign}{fmt(abs(d))}</li>' for d, r in L)
        nav = " · ".join(f'<a href="/year/{y}">{y}</a>' if y != fy else f"<b>{y}</b>" for y in D["years"])
        lede = f"In fiscal {fy}, {len(rs)} programs reported {fmt(tot)} in improper and unverifiable payments — {pct(tot/out) if out else '—'} of {fmt(out)} they paid out.{chg}"
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('Years', '/years'), (f'Fiscal {fy}', None))}
<p class="yr-nav">{nav}</p>
{f'<div class="two"><div><h2>Biggest increases</h2><ul class="mv">{mv(up, "+")}</ul></div><div><h2>Biggest drops</h2><ul class="mv">{mv(dn, "−")}</ul></div></div><p class="src">Change from fiscal {fy-1}, same program name. Our arithmetic.</p>' if movers else ''}
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>Every program that reported, fiscal {fy}</h2>
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Program</th><th>Wrong or unproven</th><th>Rate</th></tr></thead><tbody>{top}</tbody></table></div>
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
        title = f"Fiscal {fy} improper payments: {fmt(tot)}, by program | FraudBad"
        desc = f"Every federal program that reported improper payments in fiscal {fy}: {fmt(tot)} paid wrong or without proof across {len(rs)} programs."
        ds_ld = [{"@context": "https://schema.org", "@type": "Dataset",
                  "name": f"Federal improper payments by program, FY{fy}",
                  "description": desc, "url": f"{B.SITE}/year/{fy}",
                  "creator": {"@type": "Organization", "name": "Office of Management and Budget"},
                  "isBasedOn": B.S["pa_data"][3], "temporalCoverage": str(fy),
                  "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"}]
        page(B, f"year/{fy}.html", "ledger", title, desc, "og-ledger.png", "The ledger", f"Fiscal {fy}", B.e(lede), body,
             ld=ds_ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), ("Years", "/years"), (f"Fiscal {fy}", f"/year/{fy}")])


# ------------------------------------------------------------------ open data
def build_data(B):
    D = data()
    os.makedirs(os.path.join(B.OUT, "downloads"), exist_ok=True)

    def wcsv(name, header, rows):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(header)
        w.writerows(rows)
        open(os.path.join(B.OUT, "downloads", name), "w", encoding="utf-8", newline="").write(buf.getvalue())
        return len(rows)

    n1 = wcsv("improper-payments-by-program.csv", ["fiscal_year", "agency", "agency_name", "program", "outlays_musd", "improper_musd", "unknown_musd", "improper_plus_unknown_musd", "rate", "fraudbad_page"],
              [[r["fy"], r["agency"], agency_name(r["agency"]), r["program"], r["outlays"], r["improper"], r["unknown"], r["total"], r["rate"],
                (B.SITE + D["links"][(r["agency"], r["program"])]) if (r["agency"], r["program"]) in D["links"] else ""] for r in sorted(D["R"], key=lambda r: (r["fy"], r["agency"], r["program"]))])
    by_y = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in D["R"]:
        by_y[r["fy"]][0] += r["total"] or 0
        by_y[r["fy"]][1] += r["outlays"] or 0
        by_y[r["fy"]][2] += 1
    n2 = wcsv("improper-payments-by-year.csv", ["fiscal_year", "improper_plus_unknown_musd", "outlays_musd", "programs_reporting"], [[y, round(v[0], 2), round(v[1], 2), v[2]] for y, v in sorted(by_y.items())])
    cases = []
    for c in B.ORDERED:
        cases.append({"slug": c["slug"], "url": f"{B.SITE}/{c['slug']}", "title": c["title"], "type": c["type"], "level": c["level"], "place": c["place"],
                      "evidence": B.TIERS[c["tier"]][0], "figure": f"{c['fig']} {c['scale']}",
                      "receipt": [{"line": l, "value": v, "source": B.S[s][3]} for l, v, s in c["receipt"]],
                      "sources": [{"title": B.S[s][0], "publisher": B.S[s][1], "date": B.S[s][2], "url": B.S[s][3]} for s in c["sources"]]})
    json.dump({"updated": B.UPDATED, "license": "Data from U.S. government sources is public domain; FraudBad's compilation is CC BY 4.0", "cases": cases},
              open(os.path.join(B.OUT, "downloads", "cases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n3 = wcsv("cases.csv", ["slug", "url", "title", "type", "level", "place", "evidence", "figure", "first_source"],
              [[c["slug"], c["url"], c["title"], c["type"], c["level"], c["place"], c["evidence"], c["figure"], c["sources"][0]["url"] if c["sources"] else ""] for c in cases])
    mon = json.load(open(os.path.join(HERE, "data", "contracts_by_month.json")))
    mrows = []
    for fy, ms in sorted(mon.items()):
        for m in sorted([m for m in ms if m["time_period"]["fiscal_year"] == fy], key=lambda m: int(m["time_period"]["month"])):
            mrows.append([fy, int(m["time_period"]["month"]), round(m["aggregated_amount"], 2)])
    n4 = wcsv("contract-obligations-by-month.csv", ["fiscal_year", "fiscal_month", "obligations_usd"], mrows)
    n5 = wcsv("sources.csv", ["id", "title", "publisher", "date", "url"], [[k, *v] for k, v in sorted(B.S.items())])
    files = [
        ("improper-payments-by-program.csv", n1, "Every program's result for every year, FY2004–FY2025, from the government's own file. Money in millions of dollars; rate is improper plus unverifiable payments ÷ outlays."),
        ("improper-payments-by-year.csv", n2, "All programs combined, one row per fiscal year (our sums)."),
        ("cases.json", len(cases), "Every case on this site with its receipt lines, evidence level and full source list."),
        ("cases.csv", n3, "The same cases, one row each, for spreadsheets."),
        ("contract-obligations-by-month.csv", n4, "Federal contract obligations by fiscal month (October = 1), FY2018–FY2026, from USAspending.gov."),
        ("sources.csv", n5, "Every source this site cites."),
    ]
    lis = "".join(f'<tr><td><a href="/downloads/{f}" download>{f}</a></td><td class="mono">{n:,} rows</td><td>{B.e(d)}</td></tr>' for f, n, d in files)
    body = f"""<section class="sec"><div class="wrap">
<div class="tbl-wrap"><table class="tbl"><thead><tr><th>File</th><th>Size</th><th>What's in it</th></tr></thead><tbody>{lis}</tbody></table></div>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap prose">
<h2>How to cite it</h2>
<p class="cite">FraudBad, "{B.e('Improper payments by program, FY2004–FY2025')}," fraudbad.com/data, updated {B.e(B.UPDATED_HUMAN)}. Based on PaymentAccuracy.gov's FY2025 dataset.</p>
<h2>Use it</h2>
<p>Government figures are public domain. Our compilation is free to use with credit (CC BY 4.0). Charts and receipts on this site can be embedded: every case page has an embed code.</p>
<p>Found an error? <a href="/corrections">See the corrections log</a> or <a href="https://america.co/work-with-us">send the source</a>.</p>
</div></section>
{src_line(B, ['pa_data', 'usas_month'])}"""
    data_desc = "Download FraudBad open datasets: federal improper payments FY2004–FY2025, all 43 sourced cases, monthly contract obligations, and full citations."
    ds_ld = [{
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "FraudBad Open Data: Federal Improper Payments, Contracts & Sourced Fraud Cases",
        "description": data_desc, "url": B.SITE + "/data",
        "creator": {"@type": "Organization", "name": "FraudBad", "url": B.SITE},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "dateModified": B.UPDATED,
        "distribution": [
            {"@type": "DataDownload", "name": f, "encodingFormat": "application/json" if f.endswith(".json") else "text/csv",
             "contentUrl": f"{B.SITE}/downloads/{f}"}
            for f, _, _ in files
        ],
    }]
    page(B, "data.html", "", "Open data: every federal improper payment and case | FraudBad",
         data_desc, "og-ledger.png", "Open data", "The data",
         "Everything on this site comes from public records. Here it is in files you can open in a spreadsheet.", body,
         ld=ds_ld, breadcrumbs=[("Home", "/"), ("Open data", "/data")])


# ------------------------------------------------------------------ about + corrections
CORRECTIONS = [
    ("2026-11-23", "ledger", "Fixed the overpayment-recovery totals on the ledger, year pages and the improper-payments case. Our sum had counted the dataset's own \"Grand Total\" row along with the agency rows, which doubled every year's figure. Fiscal 2025 is $38.8B flagged and $23.9B recovered, not $77.5B and $47.8B. Recovery rates didn't change."),
    ("2026-11-10", "transparency", "Updated the federal \"Who got it\" cell: a law signed Sept 11, 2026 (Public Law 119-106, the Stop Secret Spending Act) now requires other transaction agreements to be reported to USAspending.gov. The page had said only that they aren't consistently reported."),
    ("2026-11-10", "health-care-waste", "Replaced a dead link to the 2019 JAMA study's press release with a news report of the same figures. The figures didn't change."),
    ("2026-11-09", "improper-payments-since-2003",
     "Updated the running total of improper payments from GAO's figure through fiscal 2024 (about $2.8 trillion) to our sum of the government's own dataset through fiscal 2025 ($2.98 trillion). Removed a line saying no government-wide recovery total is published; the dataset does report recoveries."),
    ("2026-11-09", "tax-gap", "Reworded the net tax gap so it's clearly an IRS projection, not a measured amount."),
    ("2026-11-08", "", "Site launched with 23 cases. Every figure linked to its source."),
]


def build_about(B):
    body = f"""<section class="sec"><div class="wrap prose">
<h2>What this is</h2>
<p>FraudBad collects the biggest known cases of fraud, waste and lost money in American government — federal, state and local — and links every number to the auditor, inspector general, prosecutor, court or agency report it came from.</p>
<p>It also tracks <a href="/soft-fraud">soft fraud</a>: money paid wrong, paid without proof, or never collected, which adds up to far more than the crimes. And it shows <a href="/transparency">where public spending records stop</a>.</p>
<h2>Who publishes it</h2>
<p>FraudBad is published by America House, Inc., which also runs America.co. The site has no ads and no paid placements. Reporters, researchers and anyone with a correction can reach a person at <a href="mailto:press@fraudbad.com">press@fraudbad.com</a>.</p>
<h2>Why</h2>
<p>Almost every case here was possible because nobody had to show the receipt in time for anyone to check it. Every page ends by asking you to support the <a href="__SIGN_inline__">RECEIPTS Act</a>, a citizen-authored working draft hosted on America.co. It has not been introduced in Congress. It is not S. 3902, a Senate bill on Pentagon audits that shares the name.</p>
<h2>How we judge a case</h2>
<p>Every case carries an evidence level — from proven in court to an official estimate — and a type: hard fraud (someone set out to steal) or soft fraud (money lost to errors, missing paperwork or neglect). <a href="/method">The full method</a>.</p>
<h2>What we don't do</h2>
<p>We don't name people who haven't been charged. We don't call a charge a conviction or a settlement an admission. Improper payments are not all fraud, and every page says what kind of number it shows.</p>
<h2>Corrections and contact</h2>
<p>We fix mistakes in public. Every change to a fact is listed in the <a href="/corrections">corrections log</a>. To report an error, email the source to <a href="mailto:press@fraudbad.com">press@fraudbad.com</a>.</p>
<p>The data behind every page is free to download on the <a href="/data">open data page</a>.</p>
</div></section>"""
    page(B, "about.html", "", "About FraudBad: who we are and how we work", "FraudBad links every number about fraud and waste in American government to its source. How it works, what it won't do, and how to correct it.",
         "og-home.png", "About", "About FraudBad", "Every number on this site links to the public record it came from. Here's how the site works.", body)
    rows = "".join(f'<tr><td class="mono">{d}</td><td>{f"<a href=/{s}>/{s}</a>" if s else "Whole site"}</td><td>{B.e(t)}</td></tr>' for d, s, t in CORRECTIONS)
    body = f"""<section class="sec"><div class="wrap">
<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Date</th><th>Page</th><th>What changed</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="src" style="margin-top:14px">New data added on a schedule isn't listed here. Changes to facts already published are. Every change is also in the site's <a href="https://github.com/theguysaccount/fraudbad/commits/main" rel="noopener">public history</a>.</p>
</div></section>"""
    page(B, "corrections.html", "", "Corrections log | FraudBad", "Every factual change made to FraudBad after publication, with its date.",
         "og-home.png", "Corrections", "Corrections", "When we get something wrong, we fix it here, in public, with the date.", body)


# ------------------------------------------------------------------ embeds
def build_embeds(B):
    for c in B.ORDERED:
        r = B.receipt(c["receipt"], c.get("redact"), head_title="Public receipt", head_sub=c["place"], link_mode="external", stamp=B.STAMP[c["tier"]], flat=True)
        html_ = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{B.e(c['title'])} — FraudBad receipt</title><meta name="robots" content="noindex">
<link rel="canonical" href="{B.SITE}/{c['slug']}"><link rel="stylesheet" href="/site.css?v={B.V}"></head>
<body class="embed"><div class="embed-wrap">{r}
<p class="embed-credit"><a href="{B.SITE}/{c['slug']}" target="_blank" rel="noopener"><b>{B.e(c['fig'])} {B.e(c['scale'])}</b> — {B.e(c['title'])}. Sources and the full case on <b>FraudBad</b> ↗</a></p></div>
<script src="/site.js?v={B.V}" defer></script></body></html>"""
        B.write(f"embed/{c['slug']}.html", html_)


def embed_snippet(B, c):
    code = f'<iframe src="{B.SITE}/embed/{c["slug"]}" title="{B.e(c["title"])} — FraudBad" width="100%" height="560" style="border:0;max-width:560px" loading="lazy"></iframe>'
    return f'<details class="embed-code"><summary>Embed this receipt</summary><textarea readonly rows="3" onclick="this.select()">{B.e(code)}</textarea><p class="src">Free to use with the credit link. It updates when we update the case.</p></details>'


# ------------------------------------------------------------------ feed
ADDED = {"content": "2026-11-08", "content_soft": "2026-11-09", "content_more": "2026-11-09"}


def build_feed(B, added_by_slug):
    items = []
    for c in sorted(B.ORDERED, key=lambda c: (added_by_slug.get(c["slug"], "2026-11-08"), c["slug"]), reverse=True):
        d = added_by_slug.get(c["slug"], "2026-11-08")
        items.append(f"""<item><title>{B.e(c['title'])}</title><link>{B.SITE}/{c['slug']}</link><guid>{B.SITE}/{c['slug']}</guid>
<pubDate>{_rfc822(d)}</pubDate><description>{B.e(c['dek'])}</description></item>""")
    B.write("feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>FraudBad</title><link>{B.SITE}/</link>
<atom:link href="{B.SITE}/feed.xml" rel="self" type="application/rss+xml"/>
<description>Fraud, waste and lost money in American government, with the receipts.</description><language>en-us</language>
{''.join(items)}</channel></rss>
""")


def _rfc822(d):
    import datetime
    return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a, %d %b %Y 12:00:00 +0000")


# ------------------------------------------------------------------ SSR entity & category hubs
def build_agencies_index(B):
    D = data()
    latest = max(D["years"])
    rows_data = []
    for a in D["agencies"]:
        rs = [r for r in D["R"] if r["agency"] == a]
        total = sum(r["total"] or 0 for r in rs)
        fy25 = sum(r["total"] or 0 for r in rs if r["fy"] == latest)
        progs = len({r["program"] for r in rs})
        c24 = D["COMP"].get(a, {}).get(2024)
        comp_txt = "Non-compliant" if c24 == "Non-Compliant" else ("Compliant" if c24 == "Compliant" else "—")
        rows_data.append((total, fy25, a, progs, comp_txt, min(r["fy"] for r in rs), max(r["fy"] for r in rs)))
    rows_data.sort(key=lambda t: (-t[0], t[2]))
    trs = []
    for i, (tot, fy25, a, progs, comp_txt, y0, y1) in enumerate(rows_data, 1):
        cls = "bad" if comp_txt == "Non-compliant" else ("ok" if comp_txt == "Compliant" else "")
        badge = f'<span class="cmp {cls}">{comp_txt}</span>' if cls else "—"
        trs.append(
            f'<tr><td class="rk">{i}</td><td><b><a href="/agency/{agency_slug(a)}">{B.e(agency_name(a))}</a></b>'
            f'<span class="ag">{B.e(a)} · FY{y0}–FY{y1}</span></td><td class="num">{fmt(tot)}</td>'
            f'<td class="num hide-sm">{fmt(fy25) if fy25 else "—"}</td><td class="mono hide-sm">{progs}</td>'
            f'<td class="mono">{badge}</td></tr>'
        )
    cum = sum(t[0] for t in rows_data)
    body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('All agencies', None))}
<div class="big-grid">
<div class="big"><b>{len(rows_data)}</b><span>federal agencies in OMB's improper-payment dataset</span></div>
<div class="big"><b>${cum/1e6:.2f}T</b><span>cumulative improper &amp; unproven payments, FY2004–FY{latest}</span></div>
<div class="big"><b>{sum(1 for t in rows_data if t[4] == 'Non-compliant')}</b><span>agencies rated non-compliant in FY2024</span></div>
</div></div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>All {len(rows_data)} federal agencies, ranked by cumulative total</h2>
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Agency</th><th>Total wrong/unproven</th><th class="hide-sm">FY{latest}</th><th class="hide-sm">Programs</th><th>FY2024 compliance</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
<p class="src" style="margin-top:14px">Every agency that has reported improper or unknown payments in OMB's FY2025 dataset (FY2004–FY{latest}). Explore <a href="/programs">all {len(D['links'])} programs</a> or <a href="/years">every fiscal year</a>.</p>
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
    desc = f"All {len(rows_data)} federal agencies ranked by cumulative improper and unverifiable payments (FY2004–FY{latest}), program counts, and PIIA compliance status."
    ld = [
        {"@context": "https://schema.org", "@type": "Dataset", "name": "Federal improper payments by agency, FY2004–FY2025",
         "description": desc, "url": B.SITE + "/agencies", "creator": {"@type": "Organization", "name": "Office of Management and Budget"},
         "isBasedOn": B.S["pa_data"][3], "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"},
        {"@context": "https://schema.org", "@type": "ItemList", "name": "Federal agencies reporting improper payments",
         "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{B.SITE}/agency/{agency_slug(t[2])}", "name": agency_name(t[2])}
                             for i, t in enumerate(rows_data, 1)]},
    ]
    page(B, "agencies.html", "ledger", "Federal Agencies Improper Payments Ledger (27 Agencies) | FraudBad",
         desc, "og-ledger.png", "The ledger · Agencies", "All 27 federal agencies",
         f"Every federal department and agency in OMB's improper-payment dataset, ranked by total dollars paid wrong or without proof since FY2004.",
         body, ld=ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), ("Agencies", "/agencies")])


def build_programs_index(B):
    D = data()
    items = []
    for (a, p), url in D["links"].items():
        rs = D["by_prog"][(a, p)]
        last = rs[-1]
        tot = sum(r["total"] or 0 for r in rs)
        items.append((tot, a, p, url, last, len(rs), rs[0]["fy"]))
    items.sort(key=lambda t: (-t[0], t[2]))
    trs = []
    for i, (tot, a, p, url, last, nyr, y0) in enumerate(items, 1):
        pre, core = program_parts(p)
        hay = B.e(f"{core} {pre} {a} {agency_name(a)}".lower())
        trs.append(
            f'<tr data-q="{hay}"><td class="rk">{i}</td><td><b><a href="{url}">{B.e(core)}</a></b>'
            f'<span class="ag"><a href="/agency/{agency_slug(a)}">{B.e(agency_name(a))}</a></span></td>'
            f'<td class="num">{fmt(tot)}</td><td class="mono hide-sm">FY{last["fy"]}</td>'
            f'<td class="mono">{pct(last["rate"])}</td><td class="mono hide-sm">{nyr}</td></tr>'
        )
    body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('All programs', None))}
<div class="pick"><label for="pq">Filter</label><input id="pq" type="search" placeholder="Program or agency (e.g. Medicaid, SNAP, VA, SBA)" autocomplete="off"></div>
<div class="tbl-wrap"><table class="tbl ledger fit" id="pt"><thead><tr><th>#</th><th>Program</th><th>Cumulative wrong/unproven</th><th class="hide-sm">Latest</th><th>Latest rate</th><th class="hide-sm">Years</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
<p class="src" style="margin-top:14px">Every federal program with at least {MIN_YEARS} years of official reporting in OMB's FY2025 dataset ({len(items)} programs). See also <a href="/agencies">all 27 agencies</a> and <a href="/years">all {len(D['years'])} fiscal years</a>.</p>
</div></section>
<script>
(() => {{ const q = document.getElementById('pq'), rows = [...document.querySelectorAll('#pt tbody tr')];
  q.addEventListener('input', () => {{ const s = q.value.trim().toLowerCase(); rows.forEach(r => {{ r.hidden = !!(s && !r.dataset.q.includes(s)); }}); }}); }})();
</script>
{src_line(B, ['pa_data', 'pa_site'])}"""
    desc = f"Browse all {len(items)} federal programs with 5+ years of improper-payment results in OMB's dataset, ranked by cumulative dollars paid wrong or unproven."
    ds_ld = [{"@context": "https://schema.org", "@type": "Dataset", "name": f"All {len(items)} federal programs reporting improper payments",
              "description": desc, "url": B.SITE + "/programs", "creator": {"@type": "Organization", "name": "Office of Management and Budget"},
              "isBasedOn": B.S["pa_data"][3], "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"}]
    page(B, "programs.html", "ledger", f"All {len(items)} Federal Programs: Improper Payment Histories | FraudBad",
         desc, "og-ledger.png", "The ledger · Programs", f"All {len(items)} federal programs",
         f"Every federal program with at least {MIN_YEARS} years of official improper-payment reporting, ranked by total dollars paid wrong or without proof.",
         body, ld=ds_ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), ("Programs", "/programs")])


def build_years_index(B):
    D = data()
    series = []
    trs = []
    prev_tot = None
    for fy in D["years"]:
        rs = [r for r in D["R"] if r["fy"] == fy]
        tot = sum(r["total"] or 0 for r in rs)
        out = sum(r["outlays"] or 0 for r in rs)
        series.append((fy, tot))
        chg = "—" if prev_tot is None else f"{'+' if tot - prev_tot >= 0 else '−'}{fmt(abs(tot - prev_tot))}"
        prev_tot = tot
        trs.append((fy, f'<tr><td class="mono"><b><a href="/year/{fy}">FY{fy}</a></b></td><td class="num">{fmt(tot)}</td>'
                        f'<td class="num hide-sm">{fmt(out)}</td><td class="mono">{pct(tot/out) if out else "—"}</td>'
                        f'<td class="mono hide-sm">{len(rs)}</td><td class="mono hide-sm">{chg}</td></tr>'))
    trs.reverse()
    cum = sum(v for _, v in series)
    body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), ('Years', None))}
<h2>Improper and unverifiable payments, FY{D['years'][0]}–FY{D['years'][-1]}</h2>
{year_bars(series, B, link=True)}
<p class="src" style="margin-top:14px">Cumulative total across all reporting programs: ${cum/1e6:.2f} trillion (our sum from OMB's FY2025 dataset). Click any bar or year below for that year's full program breakdown.</p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>Fiscal year</th><th>Wrong or unproven</th><th class="hide-sm">Reporting outlays</th><th>Combined rate</th><th class="hide-sm">Programs</th><th class="hide-sm">Change</th></tr></thead><tbody>{"".join(r[1] for r in trs)}</tbody></table></div>
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
    desc = f"Year-by-year archive of U.S. federal improper payments from FY{D['years'][0]} to FY{D['years'][-1]}: ${cum/1e6:.2f} trillion total across {len(D['years'])} fiscal years."
    ds_ld = [{"@context": "https://schema.org", "@type": "Dataset", "name": f"Federal improper payments by fiscal year, FY{D['years'][0]}–FY{D['years'][-1]}",
              "description": desc, "url": B.SITE + "/years", "creator": {"@type": "Organization", "name": "Office of Management and Budget"},
              "isBasedOn": B.S["pa_data"][3], "temporalCoverage": f"{D['years'][0]}/{D['years'][-1]}",
              "dateModified": B.UPDATED, "license": "https://www.usa.gov/government-works"}]
    page(B, "years.html", "ledger", f"Federal Improper Payments by Year (FY{D['years'][0]}–FY{D['years'][-1]}) | FraudBad",
         desc, "og-ledger.png", "The ledger · Archive", "Every fiscal year, FY2004–FY2025",
         f"{len(D['years'])} years of official improper-payment estimates, totaling ${cum/1e6:.2f} trillion across reporting federal programs.",
         body, ld=ds_ld, breadcrumbs=[("Home", "/"), ("The ledger", "/ledger"), ("Years", "/years")])


def build_hard_fraud(B):
    hard = [c for c in B.ORDERED if c["type"] == "hard"]
    by_lvl = {k: sum(1 for c in hard if c["level"] == k) for k in ("federal", "state", "local")}
    cards = "\n".join(B.card(c) for c in hard)
    body = f"""<section class="sec"><div class="wrap">{crumbs(('Hard fraud', None))}
<div class="big-grid">
<div class="big"><b>{len(hard)}</b><span>major hard-fraud cases tracked with official sources</span></div>
<div class="big"><b>$233–521B</b><span>estimated annual federal fraud losses (GAO-24-105833)</span></div>
<div class="big"><b>{by_lvl['federal']} / {by_lvl['state']} / {by_lvl['local']}</b><span>federal, state, and local hard-fraud cases listed below</span></div>
</div>
<p class="new-links" style="margin-top:22px"><a href="/soft-fraud">Compare with soft fraud (negligence &amp; errors) →</a><a href="/cases/federal">Federal cases →</a><a href="/cases/state">State cases →</a><a href="/cases/local">Local cases →</a></p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>Every hard-fraud case</h2>
<p style="max-width:68ch">These cases involve theft, false claims, identity fraud, criminal charges, settlements, or official fraud estimates from GAO, inspectors general, DOJ prosecutors, and state auditors. Everyone charged is presumed innocent until proven guilty.</p>
<div class="grid" style="margin-top:22px">{cards}</div>
</div></section>
{src_line(B, ['gao_fraud', 'doj_2025', 'doj_2026', 'doj_fca', 'sba_oig', 'gao_ui'])}"""
    desc = f"All {len(hard)} U.S. hard-fraud cases in FraudBad's ledger — DOJ takedowns, OIG investigations, pandemic loan theft, Medicaid schemes, and GAO's $233B–$521B/yr estimate."
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Hard fraud cases in U.S. government spending",
           "description": desc, "url": B.SITE + "/hard-fraud", "dateModified": B.UPDATED},
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Hard fraud cases",
           "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{B.SITE}/{c['slug']}", "name": c["title"]} for i, c in enumerate(hard, 1)]}]
    page(B, "hard-fraud.html", "cases", f"Hard Fraud Cases: {len(hard)} DOJ, OIG & GAO Cases | FraudBad",
         desc, "og-home.png", "Theft & deception", "Hard fraud cases",
         "Criminal schemes, false claims, DOJ takedowns, and official fraud estimates across federal, state, and local programs — every figure linked to its record.",
         body, ld=ld, breadcrumbs=[("Home", "/"), ("Hard fraud", "/hard-fraud")])


def build_case_levels(B):
    meta = {
        "federal": ("Federal government fraud and waste cases", "Federal fraud, improper payments, cost overruns, and uncollected debt across U.S. agencies — every number linked to GAO, OMB, DOJ, or an inspector general.",
                    "Federal Government Fraud & Waste Cases (OIG & GAO) | FraudBad",
                    "Every federal fraud and improper-payment case on FraudBad, sourced to GAO, DOJ, OMB, and federal inspectors general."),
        "state": ("State government fraud and audit cases", "Major state-administered program fraud, pandemic unemployment losses, Medicaid billing schemes, and transit overruns across U.S. states.",
                  "State Government Fraud & Improper Payment Cases | FraudBad",
                  "Major state-level fraud and spending cases tracked by FraudBad — Medicaid, unemployment insurance, welfare, and rail — with official audit citations."),
        "local": ("Local and municipal spending fraud cases", "City and county fraud investigations, healthcare suspensions, homelessness audits, and transit overruns cited to local auditors and watchdogs.",
                  "Local & Municipal Government Fraud Cases | FraudBad",
                  "Local government fraud investigations and spending audits tracked by FraudBad, with every figure linked to official audit and agency records."),
    }
    for lvl in ("federal", "state", "local"):
        cases = [c for c in B.ORDERED if c["level"] == lvl]
        hard_n = sum(1 for c in cases if c["type"] == "hard")
        soft_n = sum(1 for c in cases if c["type"] == "soft")
        h1, lede, title, desc = meta[lvl]
        other = "".join(f'<a href="/cases/{o}">{B.LEVELS[o]} cases →</a>' for o in ("federal", "state", "local") if o != lvl)
        extra_link = '<a href="/agencies">All 27 federal agencies →</a><a href="/ledger">Federal ledger →</a>' if lvl == "federal" else ('<a href="/states">All 51 states ranked →</a><a href="/state-audits">State single audits →</a>' if lvl == "state" else '<a href="/transparency">Local transparency gaps →</a><a href="/states">State rankings →</a>')
        cards = "\n".join(B.card(c) for c in cases)
        body = f"""<section class="sec"><div class="wrap">{crumbs(('Cases', '/'), (f'{B.LEVELS[lvl]} cases', None))}
<div class="big-grid">
<div class="big"><b>{len(cases)}</b><span>{lvl} cases in FraudBad's ledger</span></div>
<div class="big"><b>{hard_n}</b><span>hard-fraud cases (theft, charges, fraud estimates)</span></div>
<div class="big"><b>{soft_n}</b><span>soft-fraud cases (errors, overruns, missing receipts)</span></div>
</div>
<p class="new-links" style="margin-top:22px">{other}{extra_link}</p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>All {len(cases)} {lvl} cases</h2>
<div class="grid" style="margin-top:22px">{cards}</div>
</div></section>"""
        ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "description": desc,
               "url": f"{B.SITE}/cases/{lvl}", "dateModified": B.UPDATED},
              {"@context": "https://schema.org", "@type": "ItemList", "name": h1,
               "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{B.SITE}/{c['slug']}", "name": c["title"]} for i, c in enumerate(cases, 1)]}]
        page(B, f"cases/{lvl}.html", "cases", title, desc, "og-home.png", f"{B.LEVELS[lvl]} ledger", h1, lede, body,
             ld=ld, breadcrumbs=[("Home", "/"), (f"{B.LEVELS[lvl]} cases", f"/cases/{lvl}")])


def build_all(B, added_by_slug):
    rows = build_states(B)
    build_state_audits(B, rows)
    build_your_share(B, rows)
    build_contracts(B)
    build_hard_fraud(B)
    build_case_levels(B)
    build_agencies_index(B)
    build_programs_index(B)
    build_years_index(B)
    build_answers(B, rows)
    build_programs(B)
    build_agencies(B)
    build_years(B)
    build_data(B)
    build_about(B)
    build_embeds(B)
    build_ledger_embed(B)
    build_feed(B, added_by_slug)


# ------------------------------------------------------------------ states (SNAP error rates + federal awards)
STATE_CASES = {
    "MN": ["feeding-our-future", "minnesota-medicaid-programs"], "AZ": ["arizona-sober-living-fraud"],
    "CA": ["california-unemployment-fraud", "los-angeles-hospice-fraud", "california-high-speed-rail", "los-angeles-homelessness-spending"],
    "MI": ["michigan-unemployment-fraud"], "WA": ["washington-unemployment-theft"], "MS": ["mississippi-welfare-scandal"],
    "NY": ["new-york-unemployment-overpayments", "second-avenue-subway"], "HI": ["honolulu-rail"],
}
STATE_SOURCES = {
    "snap_fy25": ("SNAP payment error rates, fiscal year 2025 (by state)", "USDA Food and Nutrition Service", "Jun 24, 2026", "https://www.fns.usda.gov/sites/default/files/resource-files/snap-qcfy25-per.pdf"),
    "snap_fy24": ("SNAP payment error rates, fiscal year 2024 (by state)", "USDA Food and Nutrition Service", "Jun 30, 2025", "https://www.fns.usda.gov/sites/default/files/resource-files/snap-fy24QC-PER.pdf"),
    "usas_state": ("State profiles: federal prime awards to recipients in each state, fiscal year 2025", "USAspending.gov (U.S. Treasury), pulled by FraudBad", "Nov 10, 2026", "https://www.usaspending.gov/state"),
    "census_pop": ("State population totals, vintage 2024 (NST-EST2024)", "U.S. Census Bureau", "Dec 2024", "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv"),
    "ui_scorecard": ("UI State Performance Scorecard: improper payment and fraud rates, 12 months ending Mar 31, 2026 and 2025", "U.S. Department of Labor, Employment and Training Administration", "pulled Nov 10, 2026", "https://oui.doleta.gov/unemploy/performance/StatePerfScorecard.html"),
}


def ui_data():
    """Unemployment insurance improper-payment and fraud rates by state (DOL scorecard, Benefit Accuracy Measurement data)."""
    d = json.load(open(os.path.join(HERE, "data", "states", "ui", "ui_rates.json")))["states"]
    return d


def ui_block(B, r, ui, rank, n):
    u = ui.get(r["code"], {})
    cur, prev, us = u.get("2026-03-31"), u.get("2025-03-31"), ui["US"]["2026-03-31"]
    if not cur:
        return "<h2>Unemployment benefits paid wrong</h2><p>The Labor Department's scorecard has no improper-payment rate for this state.</p>"
    chg = ""
    if prev:
        dlt = cur["ipr"] - prev["ipr"]
        chg = f", {'up' if dlt > 0 else 'down'} from {prev['ipr']:.2f}% a year earlier"
    over = "above" if cur["ipr"] >= 10 else "under"
    fraud = f'<p>The same sample found <b>{cur["fraud"]:.2f}%</b> of benefits went out on payments the Labor Department counts as fraud (national: {us["fraud"]:.2f}%).</p>' if cur.get("fraud") is not None else ""
    prev_fraud = "—" if not prev or prev.get("fraud") is None else f"{prev['fraud']:.2f}%"
    cur_fraud = "—" if cur.get("fraud") is None else f"{cur['fraud']:.2f}%"
    prow = f'<tr><td class="mono">Apr 2024 – Mar 2025</td><td class="num">{prev["ipr"]:.2f}%</td><td class="mono">{prev_fraud}</td></tr>' if prev else ""
    return f"""<h2>Unemployment benefits paid wrong</h2>
<p class="aud-fig"><b>{cur['ipr']:.2f}%</b><span>of unemployment benefits overpaid or underpaid · #{rank[r['code']]} of {n}, #1 worst</span></p>
<p>In the 12 months ending March 31, 2026, {B.e(r['name'])} paid {cur['ipr']:.2f}% of its unemployment benefits in the wrong amount{chg}. The national rate was {us['ipr']:.2f}%. The federal goal is under 10%; {B.e(r['name'])} is {over} it.</p>{fraud}
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>12 months</th><th>Paid wrong</th><th>Fraud</th></tr></thead><tbody>
<tr><td class="mono">Apr 2025 – Mar 2026</td><td class="num">{cur['ipr']:.2f}%</td><td class="mono">{cur_fraud}</td></tr>{prow}
</tbody></table></div>
<p class="src">The Labor Department checks a random sample of each state's payments every year (its Benefit Accuracy Measurement program). Like the SNAP rate, "paid wrong" counts paying too much and too little.</p>"""


def states_data():
    snap = json.load(open(os.path.join(HERE, "data", "states", "snap_per.json")))
    us = json.load(open(os.path.join(HERE, "data", "states", "usaspending_states_fy2025.json")))["states"]
    rows = []
    for fips, s in us.items():
        k = s["name"].replace("District Of Columbia", "District of Columbia")
        sn = snap.get(k)
        if not sn or "2025" not in sn:
            continue
        rows.append({"fips": fips, "name": s["name"], "code": s["code"], "pop": s["pop2024"], "awards": s["prime_fy2025"],
                     "rate25": sn["2025"]["rate"], "over25": sn["2025"]["over"], "under25": sn["2025"]["under"],
                     "rate24": sn.get("2024", {}).get("rate")})
    rows.sort(key=lambda r: -r["rate25"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows, snap["United States"]


BASIS = {"known": "counted by the auditors", "likely": "projected by the auditors from a sample", "total": "the audit's own total for the year",
         "report": "from the auditor's own report", "none": "no dollar amount"}


def audit_block(B, code, name, heading=True):
    from state_audits import A
    a = A.get(code)
    if not a:
        return ""
    B.S[f"audit_{code}"] = (a["report"], a["auditor"], a["date"], a["url"])
    big = "" if a["basis"] == "none" else f'<p class="aud-fig"><b>{B.e(a["figure"])}</b><span>{B.e(a["program"])} · {BASIS[a["basis"]]}</span></p>'
    also = "".join(f'<p><b>Also:</b> {B.e(x["figure"])} {B.e(x["text"])} <span class="src"><a href="{B.e(x["url"])}" rel="noopener">{B.e(x["report"])}</a>, {B.e(x["date"])}</span></p>' for x in a.get("also", []))
    ref = f', finding {B.e(a["ref"])}' if a.get("ref") else ""
    h = f'<h2>What {B.e(name)}\'s auditors found</h2>' if heading else ""
    return f"""{h}{big}<p>{B.e(a["finding"])}</p>
<p class="src">{B.e(a["auditor"])}: <a href="{B.e(a["url"])}" rel="noopener">{B.e(a["report"])}</a>{ref}. Filed {B.e(a["date"])}. <a href="/state-audits">How we picked this</a>.</p>{also}"""


def build_states(B):
    B.S.update(STATE_SOURCES)
    rows, usr = states_data()
    n = len(rows)
    ui = ui_data()
    codes = {r["code"] for r in rows}
    ui_sorted = sorted((c for c in ui if c in codes and "2026-03-31" in ui[c]), key=lambda c: -ui[c]["2026-03-31"]["ipr"])
    ui_rank = {c: i for i, c in enumerate(ui_sorted, 1)}
    for r in rows:
        r["ui"] = ui.get(r["code"], {}).get("2026-03-31", {}).get("ipr")
    by_slug = {c["slug"]: c for c in B.ORDERED}
    for r in rows:
        code = r["code"].lower()
        per = r["awards"] / r["pop"]
        chg = ""
        if r["rate24"] is not None:
            d = r["rate25"] - r["rate24"]
            chg = f"{'up' if d > 0 else 'down'} {abs(d):.2f} points from {r['rate24']:.2f}% in fiscal 2024"
        cases = [by_slug[s] for s in STATE_CASES.get(r["code"], []) if s in by_slug]
        cards = "".join(B.card(c) for c in cases)
        lede = (f"In fiscal 2025, {r['name']} got {r['rate25']:.2f}% of its food-benefit (SNAP) payments wrong — "
                f"#{r['rank']} of {n}, where #1 is worst. The national rate was {usr['2025']['rate']:.2f}%.")
        body = f"""<section class="sec"><div class="wrap">{crumbs(('All states', '/states'), (B.e(r['name']), None))}
<div class="big-grid">
<div class="big"><b>{r['rate25']:.2f}%</b><span>of SNAP benefits paid in the wrong amount, fiscal 2025{', ' + chg if chg else ''}</span><i class="src">USDA</i></div>
<div class="big"><b>{fmt(r['awards']/1e6)}</b><span>in federal awards to recipients in {B.e(r['name'])}, fiscal 2025</span><i class="src">USAspending.gov</i></div>
<div class="big"><b>${per:,.0f}</b><span>per resident (our math: awards ÷ {r['pop']:,} people)</span><i class="src">USAspending.gov · Census</i></div>
</div></div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap prose">
<h2>Food benefits paid wrong</h2>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Fiscal year</th><th>Paid too much</th><th>Paid too little</th><th>Error rate</th></tr></thead><tbody>
<tr><td class="mono">2025</td><td class="mono">{r['over25']:.2f}%</td><td class="mono">{r['under25']:.2f}%</td><td class="num">{r['rate25']:.2f}%</td></tr>
{f'<tr><td class="mono">2024</td><td class="mono">—</td><td class="mono">—</td><td class="num">{r["rate24"]:.2f}%</td></tr>' if r['rate24'] is not None else ''}
</tbody></table></div>
<p class="src">USDA measures errors over a small tolerance (${57} per case in fiscal 2025). An error is not the same as fraud: the rate counts paying too much and too little.</p>
{audit_block(B, r['code'], r['name'])}
{ui_block(B, r, ui, ui_rank, len(ui_rank))}
</div></section>
{f'<section class="sec"><div class="wrap"><h2>Cases in {B.e(r["name"])}</h2><div class="grid" style="margin-top:22px">{cards}</div></div></section>' if cards else ''}
{src_line(B, ['snap_fy25', 'snap_fy24', 'ui_scorecard', 'usas_state', 'census_pop'] + ([f"audit_{r['code']}"] if f"audit_{r['code']}" in B.S else []))}"""
        st_desc = f"{r['name']} paid {r['rate25']:.2f}% of SNAP benefits wrong in FY2025 (#{r['rank']} of {n}), received {fmt(r['awards']/1e6)} in federal awards, plus UI & single-audit data."
        st_ld = [{"@context": "https://schema.org", "@type": "Dataset",
                  "name": f"{r['name']} federal awards, SNAP error rate, unemployment improper payments, and single audit",
                  "description": st_desc, "url": f"{B.SITE}/state/{code}",
                  "spatialCoverage": r["name"], "dateModified": B.UPDATED,
                  "isBasedOn": [B.S["snap_fy25"][3], B.S["ui_scorecard"][3], B.S["usas_state"][3]],
                  "license": "https://www.usa.gov/government-works"}]
        page(B, f"state/{code}.html", "", f"{r['name']}: SNAP error rate {r['rate25']:.2f}%, #{r['rank']} of {n} | FraudBad",
             st_desc, "og-ledger.png", "State", B.e(r["name"]), B.e(lede), body,
             ld=st_ld, breadcrumbs=[("Home", "/"), ("All states", "/states"), (r["name"], f"/state/{code}")])
    def _pct2(v):
        return "—" if v is None else f"{v:.2f}%"
    trs = "".join(
        f'<tr><td class="rk">{r["rank"]}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{r["rate25"]:.2f}%</td>'
        f'<td class="mono hide-sm">{_pct2(r["rate24"])}</td><td class="num">{_pct2(r["ui"])}</td><td class="mono hide-sm">${r["awards"]/r["pop"]:,.0f}</td></tr>' for r in rows)
    body = f"""<section class="sec"><div class="wrap">
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>State</th><th>SNAP error rate, FY2025</th><th class="hide-sm">FY2024</th><th>Jobless benefits paid wrong, year to Mar 2026</th><th class="hide-sm">Federal awards per resident</th></tr></thead><tbody>{trs}</tbody></table></div>
<p style="margin:0 0 18px"><a class="btn sm" href="/state-audits">What every state's own auditors found →</a></p>
<p class="src" style="margin-top:14px">Ranked worst first on SNAP. SNAP error rates: USDA. Jobless (unemployment insurance) benefits paid wrong: Labor Department scorecard. Awards per resident: our math from USAspending.gov fiscal 2025 prime awards and Census 2024 population.</p>
</div></section>
{src_line(B, ['snap_fy25', 'snap_fy24', 'ui_scorecard', 'usas_state', 'census_pop'])}"""
    states_desc = f"All {n} states and DC ranked by FY2025 SNAP payment error rates, unemployment insurance improper-payment rates, and federal awards per resident."
    states_ld = [{"@context": "https://schema.org", "@type": "Dataset",
                  "name": "U.S. state SNAP and unemployment improper payment rankings, FY2025–2026",
                  "description": states_desc, "url": B.SITE + "/states", "dateModified": B.UPDATED,
                  "isBasedOn": [B.S["snap_fy25"][3], B.S["ui_scorecard"][3], B.S["usas_state"][3]],
                  "license": "https://www.usa.gov/government-works"}]
    page(B, "states.html", "", "Every state ranked: SNAP and jobless-benefit error rates | FraudBad",
         states_desc, "og-ledger.png", "50 states + DC", "Every state, ranked",
         f"How much of its food-benefit payments each state got wrong in fiscal 2025. The national rate was {usr['2025']['rate']:.2f}%.", body,
         ld=states_ld, breadcrumbs=[("Home", "/"), ("Every state, ranked", "/states")])
    return rows


def build_state_audits(B, rows):
    """3.6: every state's own audit finding on one page."""
    from state_audits import A
    names = {r["code"]: r["name"] for r in rows}
    trs = []
    for code in sorted(A, key=lambda c: names.get(c, c)):
        a = A[code]
        B.S[f"audit_{code}"] = (a["report"], a["auditor"], a["date"], a["url"])
        fig = "—" if a["basis"] == "none" else a["figure"]
        trs.append(f'<tr><td><b><a href="/state/{code.lower()}">{B.e(names.get(code, code))}</a></b></td><td class="num">{B.e(fig)}</td>'
                   f'<td>{B.e(a["finding"])}<span class="src" style="display:block;margin-top:4px">{"" if a["basis"] == "none" else B.e(BASIS[a["basis"]].capitalize()) + ". "}'
                   f'<a href="{B.e(a["url"])}" rel="noopener">{B.e(a["auditor"])}</a>, filed {B.e(a["date"])}</span></td></tr>')
    n_none = sum(1 for a in A.values() if a["basis"] == "none")
    n_fac = sum(1 for a in A.values() if a["url"].startswith("https://app.fac.gov"))
    body = f"""<section class="sec"><div class="wrap prose">
<p>Every state that spends $1 million or more in federal money a year must get a <b>single audit</b>: an outside check of how it spent that money, filed with the federal government. Most states' own auditors do it; some hire accounting firms. When auditors find spending that broke the rules or that the state couldn't back up with records, they list it as <b>questioned costs</b>.</p>
<p>For each state we read its latest single audit ({n_fac} of {len(A)} rows) and show the largest questioned cost in it, or the report's own total when it gives one. Where the state's auditor published a bigger finding in its own report, we show that instead and say so. "Projected" means the auditors found a small amount in a sample and estimated the rest; we show both numbers.</p>
<p>Questioned costs are not fraud findings. Some are bookkeeping errors. They show where the receipts didn't hold up. {n_none} states' audits put no dollar figure on any finding.</p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>State</th><th>Amount</th><th>What the auditors found</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
<p class="src" style="margin-top:14px">Reports read Nov 10, 2026 from the <a href="https://www.fac.gov/" rel="noopener">Federal Audit Clearinghouse</a> and state auditors' sites. Seen something newer or bigger? <a href="/corrections">Tell us</a>.</p>
</div></section>
{src_line(B, [f"audit_{c}" for c in sorted(A, key=lambda c: names.get(c, c))])}"""
    sa_desc = "For all 50 states and DC, the largest questioned cost in the state's latest federal single audit, read directly from the auditor's report."
    sa_ld = [{"@context": "https://schema.org", "@type": "Dataset",
              "name": "U.S. state federal single-audit questioned costs (50 states + DC)",
              "description": sa_desc, "url": B.SITE + "/state-audits", "dateModified": B.UPDATED,
              "isBasedOn": "https://www.fac.gov/", "license": "https://www.usa.gov/government-works"}]
    page(B, "state-audits.html", "", "What every state's own auditors found | FraudBad",
         sa_desc, "og-ledger.png", "50 states + DC", "What every state's auditors found",
         "The biggest problem each state's own audit put a dollar figure on, read from the report itself.", body,
         ld=sa_ld, breadcrumbs=[("Home", "/"), ("Every state, ranked", "/states"), ("State single audits", "/state-audits")])


def build_your_share(B, rows):
    pop = sum(r["pop"] for r in rows)
    D = data()
    latest = max(D["years"])
    ip = sum(r["total"] or 0 for r in D["R"] if r["fy"] == latest) * 1e6
    lo, hi = 233e9, 521e9
    lines = [
        (f"Federal improper and unverifiable payments, FY{latest}", f"${ip/1e9:,.1f}B", "pa_data"),
        ("People in the 50 states and DC, 2024", f"{pop:,}", "census_pop"),
        ("Your share of payments made wrong (our math)", f"${ip/pop:,.0f}", "pa_data"),
        ("Lost to fraud each year, GAO estimate", "$233B–$521B", "gao_fraud"),
        ("Your share of fraud losses (our math)", f"${lo/pop:,.0f}–${hi/pop:,.0f}", "gao_fraud"),
    ]
    rc = B.receipt(lines, ("Receipt the government gave you", "NONE"), head_title="Your receipt", head_sub=f"Fiscal {latest}", link_mode="external", stamp="NO RECEIPT")
    opts = "".join(f'<option value="/state/{r["code"].lower()}">{B.e(r["name"])}</option>' for r in sorted(rows, key=lambda r: r["name"]))
    body = f"""<section class="sec"><div class="wrap two">
<div>{rc}</div>
<div class="prose"><h2>What this means</h2>
<p>Divide what the government paid wrong in one year by everyone in the country, and each person's share is about <b>${ip/pop:,.0f}</b>. Divide GAO's estimate of yearly fraud losses the same way and it's <b>${lo/pop:,.0f} to ${hi/pop:,.0f}</b>.</p>
<p>These are averages, not bills: no one is charged this. They show the size of the problem in terms anyone can picture.</p>
<h2>See your state</h2>
<form class="pick" action="/states" onsubmit="event.preventDefault();location.href=this.s.value"><label for="s">Pick a state</label><select id="s" name="s">{opts}</select><button class="btn sm" type="submit">Go</button></form>
<p><a class="btn" href="__SIGN_inline__">Ask for the receipt: sign the RECEIPTS Act ↗</a></p>
</div></div></section>
{src_line(B, ['pa_data', 'gao_fraud', 'census_pop'])}"""
    page(B, "your-share.html", "", f"Your share: ${ip/pop:,.0f} per person in federal payments made wrong | FraudBad",
         f"Federal agencies paid ${ip/1e9:,.1f} billion wrong or without proof in fiscal {latest}. That's about ${ip/pop:,.0f} for every person in the country.",
         "og-ledger.png", "Your receipt", "Your share", f"The government paid ${ip/1e9:,.1f} billion wrong in fiscal {latest}. Here's what that comes to per person.", body)


# ------------------------------------------------------------------ contract explorer (3.9)
def build_contracts(B):
    top = json.load(open(os.path.join(HERE, "data", "fy2026_top_contracts.json")))
    sig = json.load(open(os.path.join(HERE, "data", "signal_contract_descriptions.json")))
    kind = {f["id"]: f["kind"] for f in sig["flagged"]}
    label = {"blank": "No description", "code": "Only a filing code", "short": "Three words or fewer"}
    rows = []
    for t in sorted(top, key=lambda t: -t["Award Amount"]):
        k = kind.get(t["Award ID"])
        desc = (t.get("Description") or "").strip()
        url = f'https://www.usaspending.gov/award/{t["generated_internal_id"]}'
        flag = f'<span class="flag">{label[k]}</span>' if k else ""
        hay = B.e(f'{t["Recipient Name"]} {t["Awarding Agency"]} {t.get("Awarding Sub Agency") or ""} {desc} {label.get(k, "")}'.lower())
        rows.append(f'<tr data-q="{hay}" data-flag="{k or ""}"><td class="num">{fmt(t["Award Amount"]/1e6)}</td>'
                    f'<td><b>{B.e(t["Recipient Name"].title())}</b><span class="ag">{B.e(t["Awarding Agency"])}{" · " + B.e(t["Awarding Sub Agency"]) if t.get("Awarding Sub Agency") else ""}</span></td>'
                    f'<td class="mono hide-sm">{B.e(desc[:140]) if desc else "—"} {flag}</td><td><a href="{url}" rel="noopener">Record ↗</a></td></tr>')
    nflag = len(kind)
    body = f"""<section class="sec"><div class="wrap">
<div class="pick"><label for="cq">Search</label><input id="cq" type="search" placeholder="Company, agency or word" autocomplete="off">
<label class="chk"><input id="cf" type="checkbox"> Only the {nflag} with no real description</label></div>
<div class="tbl-wrap"><table class="tbl fit" id="ct"><thead><tr><th>Award amount</th><th>Who got it</th><th class="hide-sm">What the public record says it's for</th><th>Record</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="src" style="margin-top:14px">The 100 largest federal contracts with activity in fiscal 2026, from USAspending.gov ({B.e(sig['pulled'])}). "Award amount" is the contract's total to date. A short description isn't proof of waste; it means the public can't tell what was bought.</p>
</div></section>
<script>
(() => {{ const q = document.getElementById('cq'), f = document.getElementById('cf'), rows = [...document.querySelectorAll('#ct tbody tr')];
  const go = () => {{ const s = q.value.trim().toLowerCase(); rows.forEach(r => {{ r.hidden = (s && !r.dataset.q.includes(s)) || (f.checked && !r.dataset.flag); }}); }};
  q.addEventListener('input', go); f.addEventListener('change', go); }})();
</script>
{src_line(B, ['usas_signal'])}"""
    c_desc = f"Search the 100 largest federal contracts active in FY2026: {nflag} list no description, only a filing code, or three words or fewer on USAspending.gov."
    c_ld = [{"@context": "https://schema.org", "@type": "Dataset",
             "name": "Top 100 active FY2026 federal contracts and missing descriptions",
             "description": c_desc, "url": B.SITE + "/contracts", "dateModified": B.UPDATED,
             "isBasedOn": B.S["usas_signal"][3], "license": "https://www.usa.gov/government-works"}]
    page(B, "contracts.html", "soft", "The biggest federal contracts that don't say what they're for | FraudBad",
         c_desc, "og-soft-fraud.png", "Contract explorer", "What did we buy?",
         f"The 100 biggest federal contracts active this fiscal year. {nflag} of them don't say what they're for in the public record.", body,
         ld=c_ld, breadcrumbs=[("Home", "/"), ("Soft fraud", "/soft-fraud"), ("Contract explorer", "/contracts")])


# ------------------------------------------------------------------ ledger chart embed (1.4)
def build_ledger_embed(B):
    import content_more as M
    series = [(y, M.YEARS[y]["amount_m"]) for y in sorted(M.YEARS)]
    html_ = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Federal improper payments by year — FraudBad</title><meta name="robots" content="noindex">
<link rel="canonical" href="{B.SITE}/ledger"><link rel="stylesheet" href="/site.css?v={B.V}"></head>
<body class="embed"><div class="embed-wrap wide"><p class="embed-title">Federal payments made wrong or without proof, by fiscal year</p>
{year_bars(series, B)}
<p class="embed-credit"><a href="{B.SITE}/ledger" target="_blank" rel="noopener"><b>${M.CUM/1e12:.2f} trillion since {M.FIRST_YEAR}.</b> Source: PaymentAccuracy.gov (OMB). Every program on <b>FraudBad</b> ↗</a></p></div></body></html>"""
    B.write("embed/ledger.html", html_)


def embed_code(B, path, title, height):
    code = f'<iframe src="{B.SITE}/embed/{path}" title="{B.e(title)} — FraudBad" width="100%" height="{height}" style="border:0;max-width:760px" loading="lazy"></iframe>'
    return f'<details class="embed-code"><summary>Embed this chart</summary><textarea readonly rows="3" onclick="this.select()">{B.e(code)}</textarea><p class="src">Free to use with the credit link.</p></details>'


# ------------------------------------------------------------------ answer pages (3.7)
def build_answers(B, state_rows):
    import content_more as M
    D = data()
    latest = max(D["years"])
    f25 = sorted([r for r in D["R"] if r["fy"] == latest], key=lambda r: -(r["total"] or 0))
    by = {c["slug"]: c for c in B.ORDERED}

    def cards(*slugs):
        return '<div class="grid" style="margin-top:22px">' + "".join(B.card(by[x]) for x in slugs if x in by) + "</div>"

    def nm(r):
        k = (r["agency"], r["program"])
        core = program_parts(r["program"])[1]
        return f'<a href="{D["links"][k]}">{B.e(core)}</a>' if k in D["links"] else B.e(core)
    top10 = "".join(f'<tr><td class="rk">{i}</td><td><b>{nm(r)}</b><span class="ag">{B.e(agency_name(r["agency"]))}</span></td><td class="num">{fmt(r["total"])}</td><td class="mono">{pct(r["rate"])}</td></tr>' for i, r in enumerate(f25[:10], 1))
    st = sorted(state_rows, key=lambda r: -r["rate25"])
    st_rows = "".join(f'<tr><td class="rk">{r["rank"]}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{r["rate25"]:.2f}%</td></tr>' for r in st[:10])
    lo_rows = "".join(f'<tr><td class="rk">{r["rank"]}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{r["rate25"]:.2f}%</td></tr>' for r in st[-5:])
    us_rate = json.load(open(os.path.join(HERE, "data", "states", "snap_per.json")))["United States"]["2025"]["rate"]
    ui = ui_data()
    ui_list = []
    for r in state_rows:
        cur = ui.get(r["code"], {}).get("2026-03-31")
        if cur:
            ui_list.append((cur["ipr"], cur.get("fraud"), r))
    ui_list.sort(key=lambda t: -t[0])
    ui_us = ui["US"]["2026-03-31"]
    ui_hi_rows = "".join(f'<tr><td class="rk">{i}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{ipr:.2f}%</td><td class="mono">{"—" if fr is None else f"{fr:.2f}%"}</td></tr>' for i, (ipr, fr, r) in enumerate(ui_list[:10], 1))
    ui_lo_rows = "".join(f'<tr><td class="rk">{len(ui_list)-4+i}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{ipr:.2f}%</td><td class="mono">{"—" if fr is None else f"{fr:.2f}%"}</td></tr>' for i, (ipr, fr, r) in enumerate(ui_list[-5:]))
    f25_by_rate = sorted([r for r in f25 if r["rate"] is not None], key=lambda r: -r["rate"])
    top_rate_rows = "".join(f'<tr><td class="rk">{i}</td><td><b>{nm(r)}</b><span class="ag"><a href="/agency/{agency_slug(r["agency"])}">{B.e(agency_name(r["agency"]))}</a></span></td><td class="num">{pct(r["rate"])}</td><td class="num">{fmt(r["total"])}</td></tr>' for i, r in enumerate(f25_by_rate[:10], 1))
    nc_rows = []
    for a in sorted(M.NONCOMP):
        comp = D["COMP"].get(a, {})
        yrs_bad = sum(1 for v in comp.values() if v == "Non-Compliant")
        aslg = agency_slug(a)
        link = f'<a href="/agency/{aslg}">{B.e(agency_name(a))}</a>' if a in D["agencies"] else B.e(M.agency(a))
        nc_rows.append(f'<tr><td><b>{link}</b></td><td class="mono">Non-compliant (FY2024)</td><td class="mono">{yrs_bad} of {len(comp)} rated yrs</td></tr>')
    rec_years = sorted(y for y in M.REC if y >= 2016)
    rec_trs = "".join(
        f'<tr><td class="mono"><a href="/year/{y}">FY{y}</a></td><td class="num">{fmt(M.REC[y]["identified_m"])}</td>'
        f'<td class="num">{fmt(M.REC[y]["recovered_m"])}</td><td class="mono">{pct(M.REC[y]["recovered_m"]/M.REC[y]["identified_m"]) if M.REC[y]["identified_m"] else "—"}</td></tr>'
        for y in reversed(rec_years)
    )
    rec_tot_id = sum(M.REC[y]["identified_m"] for y in rec_years)
    rec_tot_got = sum(M.REC[y]["recovered_m"] for y in rec_years)
    from state_audits import A as SA
    sa_names = {r["code"]: r["name"] for r in state_rows}
    sa_quant = [c for c in sorted(SA, key=lambda c: sa_names.get(c, c)) if SA[c]["basis"] != "none"]
    sa_sample = "".join(f'<tr><td><b><a href="/state/{c.lower()}">{B.e(sa_names.get(c, c))}</a></b></td><td class="num">{B.e(SA[c]["figure"])}</td><td>{B.e(SA[c]["program"])}</td></tr>' for c in ("CA", "NY", "TX", "FL", "MN", "IL", "PA", "OH", "GA", "MI") if c in SA and SA[c]["basis"] != "none")
    sig_data = json.load(open(os.path.join(HERE, "data", "signal_contract_descriptions.json")))
    sig_blank = [f for f in sig_data["flagged"] if f["kind"] in ("blank", "code")]
    sig_short = [f for f in sig_data["flagged"] if f["kind"] == "short"]
    sig_tot_b = sum(f["amount"] for f in sig_data["flagged"]) / 1e9
    QA = [
        ("how-much-fraud-is-in-the-federal-government", "How much fraud is there in the federal government?",
         "The Government Accountability Office estimates the federal government loses $233 billion to $521 billion a year to fraud.",
         f"""<p>That's GAO's estimate, based on fiscal years 2018 through 2022. It's a range because most fraud is never caught, so it can't be counted directly.</p>
<p>A separate, official number is often confused with it: improper payments, money paid in the wrong amount, to the wrong person or without proof. Agencies reported {fmt(M.FY25/1e6)} of those in fiscal {latest}. Some improper payments are fraud; many are mistakes. <a href="/answers/what-is-an-improper-payment">What counts as an improper payment</a>.</p>
{cards("federal-fraud-estimate", "pandemic-unemployment-fraud", "ppp-eidl-loan-fraud")}""", ["gao_fraud", "pa_data"], None),
        ("what-is-an-improper-payment", "What is an improper payment?",
         f"An improper payment is federal money paid in the wrong amount, to the wrong person, or without the records to prove it was right. Agencies reported {fmt(M.FY25/1e6)} of them in fiscal {latest}.",
         f"""<p>The Payment Integrity Information Act of 2019 requires agencies to measure these payments every year, publish them and cut them. Payments the agency can't prove right or wrong are counted too, as \"unknown\" payments.</p>
<p>Most improper payments aren't fraud. By the government's own root-cause count, {fmt(M.RC_FAIL/1e6)} of fiscal {latest}'s total went out wrong even though the information to stop it existed and the agency could get to it. <a href="/data-existed-nobody-checked">More on that</a>.</p>
<p>See <a href="/ledger">every program's numbers</a>, or <a href="/answers/which-federal-programs-have-the-most-improper-payments">the ten biggest</a>.</p>""", ["omb_m2119", "pa_data", "gao_ip"], None),
        ("how-much-money-has-the-government-paid-wrong", "How much money has the federal government paid wrong?",
         f"Federal agencies have reported ${M.CUM/1e12:.2f} trillion in improper and unverifiable payments since fiscal {M.FIRST_YEAR}, by our sum of the government's own data.",
         f"""<p>Through fiscal 2024 the total is ${M.CUM24/1e12:.2f} trillion, which matches GAO's published figure of about $2.8 trillion. Fiscal {latest} alone added {fmt(M.FY25/1e6)}.</p>
<p>The total only counts programs that report. Some large programs, such as Temporary Assistance for Needy Families, have never been included.</p>
{embed_code(B, "ledger", "Federal improper payments by year", 420)}
<p><a href="/ledger">The year-by-year chart and every program →</a> · <a href="/years">Every fiscal year →</a></p>""", ["pa_data", "gao_ip_cum"], None),
        ("which-federal-programs-have-the-most-improper-payments", "Which federal programs have the most improper payments?",
         f"{program_parts(f25[0]['program'])[1]} had the most in fiscal {latest}: {fmt(f25[0]['total'])} paid wrong or without proof. The ten biggest programs made up {sum(r['total'] or 0 for r in f25[:10])/sum(r['total'] or 0 for r in f25)*100:.0f}% of the {fmt(M.FY25/1e6)} total (our math).",
         f"""<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Program</th><th>Wrong or unproven, FY{latest}</th><th>Rate</th></tr></thead><tbody>{top10}</tbody></table></div>
<p style="margin-top:18px">All {len(f25)} programs that reported are on <a href="/ledger">the ledger</a>. See also <a href="/answers/which-federal-programs-have-the-highest-error-rates">programs with the highest error rates</a>.</p>""", ["pa_data", "pa_site"], None),
        ("how-much-pandemic-money-was-lost-to-fraud", "How much pandemic relief money was lost to fraud?",
         f"Estimates run to hundreds of billions of dollars. {by['ppp-eidl-loan-fraud']['dek'] if 'ppp-eidl-loan-fraud' in by else ''}",
         f"""<p>No single official total covers every pandemic program. These are the biggest estimates, each from the agency or watchdog that made it:</p>
{cards("ppp-eidl-loan-fraud", "pandemic-unemployment-fraud", "employee-retention-credit", "feeding-our-future", "shuttered-venue-grants")}""",
         sorted({x for sl in ("ppp-eidl-loan-fraud", "pandemic-unemployment-fraud", "employee-retention-credit") if sl in by for x in by[sl]["sources"]}),
         "Official pandemic fraud estimates: $200B+ in likely SBA PPP/EIDL loan fraud, $100B–$135B in stolen unemployment benefits, and high-risk ERC claims."),
        ("which-states-have-the-highest-snap-error-rates", "Which states have the highest SNAP error rates?",
         f"{st[0]['name']} had the highest SNAP payment error rate in fiscal 2025, at {st[0]['rate25']:.2f}%. The national rate was {us_rate:.2f}%.",
         f"""<div class="two"><div><h2>Highest</h2><div class="tbl-wrap"><table class="tbl ledger fit"><tbody>{st_rows}</tbody></table></div></div>
<div><h2>Lowest</h2><div class="tbl-wrap"><table class="tbl ledger fit"><tbody>{lo_rows}</tbody></table></div></div></div>
<p style="margin-top:18px">The rate counts benefits paid too much and too little. It isn't a fraud rate. <a href="/states">All 51, ranked →</a></p>""", ["snap_fy25", "snap_fy24"], None),
        ("which-states-have-the-highest-unemployment-fraud-rates", "Which states have the highest unemployment improper payment rates?",
         f"{ui_list[0][2]['name']} had the highest unemployment improper-payment rate in the 12 months ending March 31, 2026, at {ui_list[0][0]:.2f}% (national rate: {ui_us['ipr']:.2f}%).",
         f"""<p>The U.S. Department of Labor checks a random sample of every state's unemployment benefits each year through its Benefit Accuracy Measurement scorecard. The federal compliance target is under 10%.</p>
<div class="two"><div><h2>Highest improper rates</h2><div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>State</th><th>Paid wrong</th><th>Fraud</th></tr></thead><tbody>{ui_hi_rows}</tbody></table></div></div>
<div><h2>Lowest improper rates</h2><div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>State</th><th>Paid wrong</th><th>Fraud</th></tr></thead><tbody>{ui_lo_rows}</tbody></table></div></div></div>
<p style="margin-top:18px">See <a href="/states">every state's SNAP and unemployment scores</a> and <a href="/pandemic-unemployment-fraud">pandemic UI fraud losses</a>.</p>""", ["ui_scorecard", "gao_ui"], None),
        ("which-federal-agencies-failed-payment-integrity-compliance", "Which federal agencies failed payment integrity compliance?",
         f"{len(M.NONCOMP)} of {M.N_AGENCIES} rated federal agencies were found non-compliant with the Payment Integrity Information Act (PIIA) for fiscal 2024.",
         f"""<p>Inspectors general audit each agency's payment-integrity reporting every year under the Payment Integrity Information Act of 2019. These agencies were rated non-compliant in OMB's FY2025 dataset (FY2024 compliance column):</p>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Agency</th><th>FY2024 status</th><th>History in dataset</th></tr></thead><tbody>{"".join(nc_rows)}</tbody></table></div>
<p style="margin-top:18px">Explore <a href="/agencies">all 27 federal agencies</a> and <a href="/ledger#law">the compliance breakdown on the ledger</a>.</p>""", ["pa_data", "pa_site", "omb_m2119"], None),
        ("how-much-improper-payment-money-is-recovered", "How much improper payment money does the government recover?",
         f"In fiscal 2025, federal agencies recovered {fmt(M.REC25['recovered_m'])} after flagging {fmt(M.REC25['identified_m'])} in overpayments to claw back. Since FY2016, agencies recovered {fmt(rec_tot_got)} of {fmt(rec_tot_id)} identified.",
         f"""<p>OMB's FY2025 dataset tracks overpayments agencies identified for recapture and the amounts actually recovered each fiscal year (recoveries in a year can include overpayments flagged in earlier years):</p>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Fiscal year</th><th>Flagged to recover</th><th>Recovered</th><th>Ratio</th></tr></thead><tbody>{rec_trs}</tbody></table></div>
<p style="margin-top:18px">See <a href="/ledger#recovery">the clawback chart on the ledger</a> and <a href="/federal-debt-never-collected">uncollected federal debt</a>.</p>""", ["pa_data", "treas_debt24"],
         f"In FY2025 federal agencies recovered {fmt(M.REC25['recovered_m'])} of {fmt(M.REC25['identified_m'])} flagged; since FY2016, {fmt(rec_tot_got)} of {fmt(rec_tot_id)} identified."),
        ("which-federal-programs-have-the-highest-error-rates", "Which federal programs have the highest improper payment rates?",
         f"{program_parts(f25_by_rate[0]['program'])[1]} had the highest improper-payment rate in fiscal {latest} at {pct(f25_by_rate[0]['rate'])}. Overall, {M.OVER10} programs had error rates of 10% or higher.",
         f"""<p>Dollar totals are dominated by massive programs like Medicare and Medicaid. Ranking by error rate shows which programs lose the largest share of every dollar paid out:</p>
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Program</th><th>FY{latest} rate</th><th>Wrong/unproven</th></tr></thead><tbody>{top_rate_rows}</tbody></table></div>
<p style="margin-top:18px">Compare against <a href="/answers/which-federal-programs-have-the-most-improper-payments">programs with the largest dollar totals</a> or browse <a href="/programs">all {len(D['links'])} programs</a>.</p>""", ["pa_data", "pa_site"],
         f"{program_parts(f25_by_rate[0]['program'])[1]} topped FY{latest} at {pct(f25_by_rate[0]['rate'])}. See the 10 federal programs with the highest improper payment rates."),
        ("what-did-state-auditors-find-in-federal-single-audits", "What did state auditors find in federal single audits?",
         f"Across all 50 states and DC, {len(sa_quant)} states' latest federal single audits put a dollar figure on questioned costs where spending broke rules or lacked records.",
         f"""<p>Any state spending $1 million or more in federal funds must file an independent single audit with the Federal Audit Clearinghouse. Highlighted large-state findings from our 51-state review:</p>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>State</th><th>Questioned / audit figure</th><th>Program audited</th></tr></thead><tbody>{sa_sample}</tbody></table></div>
<p style="margin-top:18px">Read all 51 findings with source links on <a href="/state-audits">What every state's own auditors found</a>.</p>""", ["usas_state"], None),
        ("which-federal-contracts-have-no-description", "Which major federal contracts have no public description?",
         f"Among the 100 largest federal contracts active in FY2026 on USAspending.gov, {len(sig_data['flagged'])} totaling ${sig_tot_b:,.1f}B have blank descriptions, filing codes only, or three words or fewer.",
         f"""<p>FraudBad pulled the 100 largest active FY2026 contract awards from USAspending.gov: {len(sig_blank)} had blank descriptions or only filing codes, and {len(sig_short)} more used three words or fewer. A missing description is not proof of waste — it means taxpayers cannot see what was purchased.</p>
{cards("contracts-with-no-description", "september-spending-rush")}
<p style="margin-top:18px">Search all 100 contracts in the <a href="/contracts">Contract explorer</a>.</p>""", ["usas_signal", "usas_month"],
         f"{len(sig_data['flagged'])} of the 100 largest FY2026 federal contracts (${sig_tot_b:,.1f}B) list blank descriptions, filing codes only, or three words or fewer."),
    ]
    items = []
    for slug_, q, a, more, srcs, custom_desc in QA:
        ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}]}]
        body = f"""<section class="sec"><div class="wrap prose">{crumbs(('Answers', '/answers/'), (B.e(q), None))}
<p class="answer">{B.e(a)}</p>{more}</div></section>
{src_line(B, srcs)}"""
        desc = custom_desc if custom_desc else a
        page(B, f"answers/{slug_}.html", "", [f"{q} | FraudBad", q], desc, "og-home.png", "Answer", B.e(q), "", body,
             ld=ld, breadcrumbs=[("Home", "/"), ("Answers", "/answers/"), (q, f"/answers/{slug_}")])
        items.append(f'<li><a href="/answers/{slug_}">{B.e(q)}</a><span>{B.e(a)}</span></li>')
    body = f"""<section class="sec"><div class="wrap prose"><ul class="answers">{"".join(items)}</ul></div></section>"""
    page(B, "answers/index.html", "", "Fraud and waste questions, answered with sources | FraudBad",
         "Short, sourced answers to the most common questions about fraud, improper payments and waste in American government.",
         "og-home.png", "Answers", "Straight answers", "The questions people ask most, each answered with one sourced number first.", body,
         breadcrumbs=[("Home", "/"), ("Answers", "/answers/")])
