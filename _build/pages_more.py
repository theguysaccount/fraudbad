# -*- coding: utf-8 -*-
"""Phase 1 and Phase 3 pages: about, corrections, open data, embeds, feed, and one page for every
program, agency and fiscal year in the government's own improper-payment file.

Every number here is read from data/pa/FY2025_Dataset.xlsx (PaymentAccuracy.gov) or from the case files.
Sums and ranks are ours and are labelled that way on the page."""
import collections, csv, io, json, os, re
import openpyxl

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
        return head.strip(), tail.strip()
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


def data():
    if _D:
        return _D
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb["All Program Results "].iter_rows(values_only=True))
    H = rows[0]
    R = []
    for r in rows[1:]:
        if not r[0]:
            continue
        d = dict(zip(H, r))
        R.append({"agency": d["Agency"].strip(), "program": " ".join(str(d["Program Name"]).split()), "fy": int(d["Fiscal Year"]),
                  "outlays": d["Outlays Amount ($M)"], "improper": d["Improper Payment Amount ($M)"],
                  "unknown": d["Unknown Payment Amount  ($M)"], "total": d["Improper Payment and Unknown Payment Amount ($M)"] or 0,
                  "rate": d["Improper Payment and Unknown Payment Rate"], "over": d["Total Overpayments Amount ($M)"],
                  "under": d["Underpayment Amount ($M)"]})
    rc_rows = list(wb["Improper Payment Root Causes"].iter_rows(values_only=True))
    RH = rc_rows[0]
    RC = collections.defaultdict(lambda: collections.defaultdict(float))  # (agency, program, fy) -> cause -> $M
    for r in rc_rows[1:]:
        if not r[0]:
            continue
        key = (r[0].strip(), " ".join(str(r[1]).split()), int(r[3]))
        for i in range(4, len(RH)):
            if isinstance(r[i], (int, float)):
                RC[key][RH[i].strip()] += r[i]
    rec_rows = list(wb["Rate and Amt of Recovery"].iter_rows(values_only=True))
    RRH = [str(h).strip() if h else "" for h in rec_rows[0]]
    REC = collections.defaultdict(dict)  # agency -> fy -> (identified, recovered)
    for r in rec_rows[1:]:
        if not r[0]:
            continue
        a = str(r[0]).strip()
        for i, h in enumerate(RRH):
            m = re.match(r"(\d{4}) Overpayment Amount Identified", h)
            if m and isinstance(r[i], (int, float)) and isinstance(r[i + 1], (int, float)):
                REC[a][int(m.group(1))] = (r[i], r[i + 1])
    ct = list(wb["Compliance Trend Table"].iter_rows(values_only=True))
    CH = ct[1]
    COMP = {}
    for r in ct[2:]:
        if r[0] and isinstance(r[0], str) and not str(r[0]).replace(".", "").isdigit():
            COMP[r[0].strip()] = {int(CH[i]): r[i] for i in range(1, len(CH)) if isinstance(CH[i], int) and r[i] in ("Compliant", "Non-Compliant")}
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


def page(B, path, active, title, desc, og, kicker, h1, lede, body, ld=None):
    url_path = "/" + (path[:-10] if path.endswith("/index.html") else path[:-5])
    head = B.head(title, desc, url_path, og, [B.ORG_LD] + (ld or []))
    hero = f"""<section class="page-hero"><div class="wrap">
<p class="kicker" style="color:#ff4438">{kicker}</p><h1 class="h1-mid">{h1}</h1><p class="lede">{lede}</p></div></section>"""
    B.write(path, head + B.header(active) + '<main id="main">' + hero + body + "</main>" + B.cta() + B.footer())
    if path.endswith(".html") and not path.startswith("embed/"):
        u = "/" + (path[:-10] if path.endswith("/index.html") else path[:-5])
        B.EXTRA_URLS.append(u)


def crumbs(*items):
    parts = [f'<a href="{h}">{t}</a>' if h else f"<span>{t}</span>" for t, h in items]
    return f'<nav class="crumbs" aria-label="Breadcrumb">{" / ".join(parts)}</nav>'


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
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), (B.e(agency_name(a)), f'/agency/{agency_slug(a)}'), (B.e(program_parts(p)[1]), None))}
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
<section class="sec"><div class="wrap prose">{rc_html}<p>{comp_line} <a href="/agency/{agency_slug(a)}">Every {B.e(a)} program →</a></p>
<p class="src">Improper payments include mistakes and missing paperwork as well as fraud. This page shows how much, not why in any one case.</p></div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
        title = f"{p} ({a}): improper payments by year | FraudBad"
        desc = f"{p}, {agency_name(a)}: {fmt(total)} paid wrong or without proof over {len(rs)} years of official results. Latest: {pct(last['rate'])} in fiscal {last['fy']}."
        pre, core = program_parts(p)
        page(B, url[1:] + ".html", "ledger", title[:120], desc, "og-ledger.png", B.e(agency_name(a) + (" · " + pre if pre else "")), B.e(core), B.e(lede), body)


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
        cur = sorted([r for r in rs if r["fy"] == latest], key=lambda r: -(r["total"] or 0))
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
        lede = (f"{agency_name(a)} has reported {fmt(total)} in improper and unverifiable payments across {len(progs)} programs since fiscal {series[0][0]}, by our sum of its own reports."
                + (f" In fiscal {latest}: {fmt(by_y[latest])}." if latest in by_y else ""))
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), (B.e(agency_name(a)), None))}
<h2>Paid wrong, year by year</h2>{year_bars(series, B, link=True)}
<p class="src">All of {B.e(a)}'s reporting programs combined, each fiscal year. Bars link to that year.</p></div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>Every program it has reported</h2>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Program</th><th>Latest year</th><th>Wrong or unproven</th><th class="hide-sm">Rate</th><th class="hide-sm">Years reported</th></tr></thead><tbody>{''.join(r[2] for r in rows)}</tbody></table></div>
</div></section>
<section class="sec"><div class="wrap prose">
{f'<h2>Did it follow the payment-integrity law?</h2><p class="cmp-row">{comp_cells}</p><p class="src">Red = rated out of compliance by its inspector general that fiscal year. Green = compliant.</p>' if comp else ''}
{f'<h2>Overpayments flagged and recovered</h2><div class="tbl-wrap"><table class="tbl" style="min-width:0"><thead><tr><th>Year</th><th>Flagged to recover</th><th>Recovered</th></tr></thead><tbody>{rec_rows}</tbody></table></div>' if rec_rows else ''}
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
        title = f"{agency_name(a)}: every improper payment it has reported | FraudBad"
        desc = f"{agency_name(a)}: {fmt(total)} in improper and unverifiable payments since fiscal {series[0][0]}, program by program, from the government's own data."
        page(B, f"agency/{agency_slug(a)}.html", "ledger", title[:120], desc, "og-ledger.png", "Agency", B.e(agency_name(a)), B.e(lede), body)


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
        top = "".join(f'<tr><td class="rk">{i}</td><td><b>{nm(r)}</b><span class="ag">{B.e(agency_name(r["agency"]))}</span></td><td class="num">{fmt(r["total"])}</td><td class="mono">{pct(r["rate"])}</td></tr>' for i, r in enumerate(rs, 1))
        mv = lambda L, sign: "".join(f'<li>{nm(r)}: {sign}{fmt(abs(d))}</li>' for d, r in L)
        nav = " · ".join(f'<a href="/year/{y}">{y}</a>' if y != fy else f"<b>{y}</b>" for y in D["years"])
        lede = f"In fiscal {fy}, {len(rs)} programs reported {fmt(tot)} in improper and unverifiable payments — {pct(tot/out) if out else '—'} of {fmt(out)} they paid out.{chg}"
        body = f"""<section class="sec"><div class="wrap">{crumbs(('The ledger', '/ledger'), (f'Fiscal {fy}', None))}
<p class="yr-nav">{nav}</p>
{f'<div class="two"><div><h2>Biggest increases</h2><ul class="mv">{mv(up, "+")}</ul></div><div><h2>Biggest drops</h2><ul class="mv">{mv(dn, "−")}</ul></div></div><p class="src">Change from fiscal {fy-1}, same program name. Our arithmetic.</p>' if movers else ''}
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<h2>Every program that reported, fiscal {fy}</h2>
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Program</th><th>Wrong or unproven</th><th>Rate</th></tr></thead><tbody>{top}</tbody></table></div>
</div></section>
{src_line(B, ['pa_data', 'pa_site'])}"""
        title = f"Fiscal {fy}: {fmt(tot)} in improper federal payments, program by program | FraudBad"
        desc = f"Every federal program that reported improper payments in fiscal {fy}: {fmt(tot)} paid wrong or without proof across {len(rs)} programs."
        page(B, f"year/{fy}.html", "ledger", title, desc, "og-ledger.png", "The ledger", f"Fiscal {fy}", B.e(lede), body)


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
    page(B, "data.html", "", "Open data: every federal improper payment, every case, every source | FraudBad",
         "Download the data behind FraudBad: every federal program's improper payments FY2004–FY2025, every case with its sources, and monthly contract spending.",
         "og-ledger.png", "Open data", "The data", "Everything on this site comes from public records. Here it is in files you can open in a spreadsheet.", body)


# ------------------------------------------------------------------ about + corrections
CORRECTIONS = [
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
<h2>Why</h2>
<p>Almost every case here was possible because nobody had to show the receipt in time for anyone to check it. Every page ends by asking you to support the <a href="__SIGN_inline__">RECEIPTS Act</a>, a citizen-authored working draft hosted on America.co. It has not been introduced in Congress.</p>
<h2>How we judge a case</h2>
<p>Every case carries an evidence level — from proven in court to an official estimate — and a type: hard fraud (someone set out to steal) or soft fraud (money lost to errors, missing paperwork or neglect). <a href="/method">The full method</a>.</p>
<h2>What we don't do</h2>
<p>We don't name people who haven't been charged. We don't call a charge a conviction or a settlement an admission. Improper payments are not all fraud, and every page says what kind of number it shows.</p>
<h2>Corrections and contact</h2>
<p>We fix mistakes in public. Every change to a fact is listed in the <a href="/corrections">corrections log</a>. To report an error, <a href="https://america.co/work-with-us">send us the source</a>.</p>
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


def build_all(B, added_by_slug):
    rows = build_states(B)
    build_your_share(B, rows)
    build_contracts(B)
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
}


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


def build_states(B):
    B.S.update(STATE_SOURCES)
    rows, usr = states_data()
    n = len(rows)
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
<h2>Unemployment insurance</h2>
<p>The Labor Department publishes every state's unemployment-insurance error rate on its <a href="https://www.dol.gov/agencies/eta/unemployment-insurance-payment-accuracy" rel="noopener">payment accuracy page</a>. We'll add it here.</p>
</div></section>
{f'<section class="sec"><div class="wrap"><h2>Cases in {B.e(r["name"])}</h2><div class="grid" style="margin-top:22px">{cards}</div></div></section>' if cards else ''}
{src_line(B, ['snap_fy25', 'snap_fy24', 'usas_state', 'census_pop'])}"""
        page(B, f"state/{code}.html", "", f"{r['name']}: SNAP error rate {r['rate25']:.2f}% (#{r['rank']} of {n}) and federal spending | FraudBad",
             f"{r['name']} paid {r['rate25']:.2f}% of SNAP food benefits wrong in fiscal 2025, #{r['rank']} of {n}. Plus {fmt(r['awards']/1e6)} in federal awards and every FraudBad case in the state.",
             "og-ledger.png", "State", B.e(r["name"]), B.e(lede), body)
    trs = "".join(
        f'<tr><td class="rk">{r["rank"]}</td><td><b><a href="/state/{r["code"].lower()}">{B.e(r["name"])}</a></b></td><td class="num">{r["rate25"]:.2f}%</td>'
        f'<td class="mono hide-sm">{"—" if r["rate24"] is None else f"{r["rate24"]:.2f}%"}</td><td class="mono">${r["awards"]/r["pop"]:,.0f}</td></tr>' for r in rows)
    body = f"""<section class="sec"><div class="wrap">
<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>State</th><th>SNAP error rate, FY2025</th><th class="hide-sm">FY2024</th><th>Federal awards per resident</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="src" style="margin-top:14px">Ranked worst first. Error rates: USDA. Awards per resident: our math from USAspending.gov fiscal 2025 prime awards and Census 2024 population.</p>
</div></section>
{src_line(B, ['snap_fy25', 'snap_fy24', 'usas_state', 'census_pop'])}"""
    page(B, "states.html", "", "Every state ranked: SNAP payment error rates and federal spending | FraudBad",
         f"All {n} states and DC ranked by how much of their SNAP food benefits they paid wrong in fiscal 2025, with federal awards per resident.",
         "og-ledger.png", "50 states + DC", "Every state, ranked", f"How much of its food-benefit payments each state got wrong in fiscal 2025. The national rate was {usr['2025']['rate']:.2f}%.", body)
    return rows


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
    page(B, "contracts.html", "soft", "The 100 biggest federal contracts, and which ones don't say what they're for | FraudBad",
         f"Search the 100 largest federal contracts active in fiscal 2026. {nflag} of them list no description, only a filing code, or three words or fewer.",
         "og-soft-fraud.png", "Contract explorer", "What did we buy?", f"The 100 biggest federal contracts active this fiscal year. {nflag} of them don't say what they're for in the public record.", body)


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
    QA = [
        ("how-much-fraud-is-in-the-federal-government", "How much fraud is there in the federal government?",
         "The Government Accountability Office estimates the federal government loses $233 billion to $521 billion a year to fraud.",
         f"""<p>That's GAO's estimate, based on fiscal years 2018 through 2022. It's a range because most fraud is never caught, so it can't be counted directly.</p>
<p>A separate, official number is often confused with it: improper payments, money paid in the wrong amount, to the wrong person or without proof. Agencies reported {fmt(M.FY25/1e6)} of those in fiscal {latest}. Some improper payments are fraud; many are mistakes. <a href="/answers/what-is-an-improper-payment">What counts as an improper payment</a>.</p>
{cards("federal-fraud-estimate", "pandemic-unemployment-fraud", "ppp-eidl-loan-fraud")}""", ["gao_fraud", "pa_data"]),
        ("what-is-an-improper-payment", "What is an improper payment?",
         f"An improper payment is federal money paid in the wrong amount, to the wrong person, or without the records to prove it was right. Agencies reported {fmt(M.FY25/1e6)} of them in fiscal {latest}.",
         f"""<p>The Payment Integrity Information Act of 2019 requires agencies to measure these payments every year, publish them and cut them. Payments the agency can't prove right or wrong are counted too, as \"unknown\" payments.</p>
<p>Most improper payments aren't fraud. By the government's own root-cause count, {fmt(M.RC_FAIL/1e6)} of fiscal {latest}'s total went out wrong even though the information to stop it existed and the agency could get to it. <a href="/data-existed-nobody-checked">More on that</a>.</p>
<p>See <a href="/ledger">every program's numbers</a>, or <a href="/answers/which-federal-programs-have-the-most-improper-payments">the ten biggest</a>.</p>""", ["omb_m2119", "pa_data", "gao_ip"]),
        ("how-much-money-has-the-government-paid-wrong", "How much money has the federal government paid wrong?",
         f"Federal agencies have reported ${M.CUM/1e12:.2f} trillion in improper and unverifiable payments since fiscal {M.FIRST_YEAR}, by our sum of the government's own data.",
         f"""<p>Through fiscal 2024 the total is ${M.CUM24/1e12:.2f} trillion, which matches GAO's published figure of about $2.8 trillion. Fiscal {latest} alone added {fmt(M.FY25/1e6)}.</p>
<p>The total only counts programs that report. Some large programs, such as Temporary Assistance for Needy Families, have never been included.</p>
{embed_code(B, "ledger", "Federal improper payments by year", 420)}
<p><a href="/ledger">The year-by-year chart and every program →</a></p>""", ["pa_data", "gao_ip_cum"]),
        ("which-federal-programs-have-the-most-improper-payments", "Which federal programs have the most improper payments?",
         f"{program_parts(f25[0]['program'])[1]} had the most in fiscal {latest}: {fmt(f25[0]['total'])} paid wrong or without proof. The ten biggest programs made up {sum(r['total'] or 0 for r in f25[:10])/sum(r['total'] or 0 for r in f25)*100:.0f}% of the {fmt(M.FY25/1e6)} total (our math).",
         f"""<div class="tbl-wrap"><table class="tbl ledger fit"><thead><tr><th>#</th><th>Program</th><th>Wrong or unproven, FY{latest}</th><th>Rate</th></tr></thead><tbody>{top10}</tbody></table></div>
<p style="margin-top:18px">All {len(f25)} programs that reported are on <a href="/ledger">the ledger</a>.</p>""", ["pa_data", "pa_site"]),
        ("how-much-pandemic-money-was-lost-to-fraud", "How much pandemic relief money was lost to fraud?",
         f"Estimates run to hundreds of billions of dollars. {by['ppp-eidl-loan-fraud']['dek'] if 'ppp-eidl-loan-fraud' in by else ''}",
         f"""<p>No single official total covers every pandemic program. These are the biggest estimates, each from the agency or watchdog that made it:</p>
{cards("ppp-eidl-loan-fraud", "pandemic-unemployment-fraud", "employee-retention-credit", "feeding-our-future", "shuttered-venue-grants")}""",
         sorted({x for sl in ("ppp-eidl-loan-fraud", "pandemic-unemployment-fraud", "employee-retention-credit") if sl in by for x in by[sl]["sources"]})),
        ("which-states-have-the-highest-snap-error-rates", "Which states have the highest SNAP error rates?",
         f"{st[0]['name']} had the highest SNAP payment error rate in fiscal 2025, at {st[0]['rate25']:.2f}%. The national rate was {us_rate:.2f}%.",
         f"""<div class="two"><div><h2>Highest</h2><div class="tbl-wrap"><table class="tbl ledger fit"><tbody>{st_rows}</tbody></table></div></div>
<div><h2>Lowest</h2><div class="tbl-wrap"><table class="tbl ledger fit"><tbody>{lo_rows}</tbody></table></div></div></div>
<p style="margin-top:18px">The rate counts benefits paid too much and too little. It isn't a fraud rate. <a href="/states">All 51, ranked →</a></p>""", ["snap_fy25", "snap_fy24"]),
    ]
    items = []
    for slug_, q, a, more, srcs in QA:
        ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}]}]
        body = f"""<section class="sec"><div class="wrap prose">{crumbs(('Answers', '/answers'), (B.e(q), None))}
<p class="answer">{B.e(a)}</p>{more}</div></section>
{src_line(B, srcs)}"""
        page(B, f"answers/{slug_}.html", "", f"{q} | FraudBad", a[:300], "og-home.png", "Answer", B.e(q), "", body, ld)
        items.append(f'<li><a href="/answers/{slug_}">{B.e(q)}</a><span>{B.e(a)}</span></li>')
    body = f"""<section class="sec"><div class="wrap prose"><ul class="answers">{"".join(items)}</ul></div></section>"""
    page(B, "answers/index.html", "", "Questions about government fraud and waste, answered with sources | FraudBad",
         "Short, sourced answers to the most common questions about fraud, improper payments and waste in American government.",
         "og-home.png", "Answers", "Straight answers", "The questions people ask most, each answered with one sourced number first.", body)
