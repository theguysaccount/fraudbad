# -*- coding: utf-8 -*-
"""Build fraudbad.com into ./site as flat static files (GitHub Pages serves /slug from slug.html)."""
import html, json, os, shutil, re, urllib.parse
from content import GSC_FILE, INDEXNOW_KEY
from content import (UPDATED, UPDATED_HUMAN, SITE, CTA_URL, SOCIALS, S, TIERS, LEVELS, CASES,
                     DIVE_ROWS, DIVE, DARK_MONEY, LOCAL_TYPES)
import content_soft  # noqa: F401  (adds soft-fraud cases, tiers and sources)
from content_soft import TYPES, SIGNALS, SOFT_BIG, BLANK, SHORT, BLANK_TOTAL, SHORT_TOTAL, TOP_TOTAL, SIG
import content_more as M  # official improper-payment ledger + round-3 cases

OUT = os.path.join(os.path.dirname(__file__), "site")
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
V = "20261110"
e = lambda s: html.escape(str(s), quote=True)

LEVEL_ORDER = {"federal": 0, "state": 1, "local": 2}
ORDER = [
    # hard fraud
    "federal-fraud-estimate", "pandemic-unemployment-fraud", "ppp-eidl-loan-fraud", "employee-retention-credit",
    "operation-gold-rush", "health-care-fraud-takedown-2026", "minnesota-medicaid-programs", "california-unemployment-fraud",
    "michigan-unemployment-fraud", "arizona-sober-living-fraud", "washington-unemployment-theft", "feeding-our-future",
    "mississippi-welfare-scandal", "los-angeles-hospice-fraud", "false-claims-act-2025", "snap-card-skimming",
    # soft fraud
    "improper-payments-since-2003", "medicare-advantage-overpayments", "health-care-waste", "tax-gap", "unfixed-gao-savings",
    "federal-debt-never-collected", "improper-payments-2025", "data-existed-nobody-checked", "september-spending-rush",
    "california-high-speed-rail", "contracts-with-no-description", "sentinel-icbm-overrun", "weapons-cost-overruns",
    "federal-it-legacy-systems", "medicare-medicaid-no-receipts", "pentagon-failed-audits", "social-security-overpayments",
    "shuttered-venue-grants", "afghanistan-reconstruction", "tax-credit-errors", "snap-payment-errors",
    "hud-rental-assistance-unverified", "honolulu-rail", "second-avenue-subway", "medicare-generic-drug-prices",
    "new-york-unemployment-overpayments", "los-angeles-homelessness-spending"]
_by = {c["slug"]: c for c in CASES}
assert sorted(ORDER) == sorted(_by), "ORDER must list every case exactly once"
ORDERED = [_by[s] for s in ORDER]
PROGRAM_LINKS = {}  # (agency, program) -> /program/<slug>
EXTRA_URLS = []  # pages added by pages_more (program, agency, year, data, about...)

STAMP = {"confirmed": "CONFIRMED", "charged": "CHARGED", "settled": "SETTLED", "estimated": "NO RECEIPT",
         "noproof": "NO RECEIPT", "frozen": "FROZEN", "unauditable": "UNAUDITABLE",
         "overrun": "OVER BUDGET", "unfixed": "NOT FIXED", "measured": "MEASURED", "uncollected": "UNCOLLECTED"}


def src_title(sid):
    t, pub, date, url = S[sid]
    return f"{pub}, {date}: {t}"


def head(title, desc, path, og, jsonld=None, extra=""):
    url = SITE + path
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    return f"""<!doctype html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#0a1f44">
<meta property="og:type" content="{ 'article' if path.count('/')==1 and path!='/' and path not in ('/transparency','/method') else 'website'}">
<meta property="og:site_name" content="FraudBad">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{SITE}/{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/{og}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/anton-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/site.css?v={V}">
{ld}{extra}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


def header(active=""):
    def a(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    return f"""<header class="top"><div class="wrap">
<a class="mark" href="/" aria-label="FraudBad home"><span class="f">Fraud</span><span class="b">Bad</span><small>No taxation without receipts</small></a>
<nav class="nav" aria-label="Main">{a('/#cases','The cases','cases')}{a('/soft-fraud','Soft fraud','soft')}{a('/ledger','The ledger','ledger')}{a('/transparency','Where receipts stop','transparency')}{a('/method','How we judge','method')}<a class="btn sm" href="__SIGN_nav__">Sign the Receipts Act</a></nav>
</div></header>
"""


def social_links():
    return " ".join(f'<a href="{u}" rel="noopener">{n}</a>' for n, u in SOCIALS)


def cta():
    return f"""<section class="cta" aria-labelledby="cta-h"><div class="wrap">
<div>
<p class="kicker">America.co · The RECEIPTS Act</p>
<h2 id="cta-h">Want to stop it?<span>Sign the Receipts Act.</span></h2>
<p class="cta-line" data-b="Every number on this site was counted after the money was already spent. The RECEIPTS Act starts with one rule: when the government buys from GSA's catalog for over $25,000, it publishes the price next to what other agencies paid for the same thing. Add your name.">Public money should come with a receipt anyone can check. The RECEIPTS Act starts with one rule for federal purchases over $25,000 from GSA's buying catalog: publish the price paid next to what other agencies paid for the same thing.</p>
</div>
<div class="side">
<a class="btn white" href="__SIGN_band__">Sign the Receipts Act ↗</a>
<p class="follow">Follow the movement: {social_links()}</p>
<p class="note">A citizen-authored working draft hosted on America.co. It has not been introduced in Congress.</p>
</div>
</div></section>
"""


def footer():
    return f"""<footer class="foot"><div class="wrap">
<div><a class="mark" href="/"><span class="f">Fraud</span><span class="b">Bad</span></a>
<p style="margin-top:14px">An independent public-interest site. Not a government website. Every figure links to the auditor, inspector general, court record or agency report it came from.</p></div>
<nav aria-label="Site"><a href="/#cases">All cases</a><a href="/soft-fraud">Soft fraud</a><a href="/ledger">Every program's error rate</a><a href="/transparency">Where the receipts stop</a><a href="/method">How we judge cases</a><a href="/data">Open data</a><a href="/about">About</a><a href="/corrections">Corrections</a><a href="__SIGN_footer__">Sign the Receipts Act</a></nav>
<nav aria-label="America.co"><a href="https://america.co/">America.co</a>{''.join(f'<a href="{u}" rel="noopener">{n}</a>' for n,u in SOCIALS)}<a href="https://america.co/work-with-us">Send a correction</a></nav>
<p class="fine">Updated {UPDATED_HUMAN}. Charges are accusations; everyone charged is presumed innocent until proven guilty. Improper payments are not all fraud — each page says what kind of number it is.</p>
</div></footer>
<div class="signbar" aria-hidden="true"><span>Want to stop it?</span><a class="btn sm" href="__SIGN_bar__" tabindex="-1">Sign the Receipts Act</a></div>
<script src="/site.js?v={V}" defer></script>
</body></html>
"""


def receipt(lines, redact=None, head_title="Public receipt", head_sub="", foot=("fraudbad.com", "No taxation without receipts"), stamp="NO RECEIPT", link_mode="anchor", srcmap=None, flat=False):
    lis = []
    for label, val, sid in lines:
        if link_mode == "anchor" and srcmap is not None:
            n = srcmap[sid]
            sup = f'<sup class="n"><a href="#s-{n}" title="{e(src_title(sid))}">{n}</a></sup>'
        else:
            sup = f'<sup class="n"><a href="{e(S[sid][3])}" rel="noopener" title="{e(src_title(sid))}">↗</a></sup>'
        lis.append(f'<li><span class="r-label">{e(label)}</span><span class="r-dots"></span><span class="r-val">{e(val)}</span>{sup}</li>')
    if redact:
        lab, say = redact
        lis.append(f'<li class="redact"><span class="r-label">{e(lab)}</span><span class="r-dots"></span><span class="r-val" data-say="{e(say)}">████████████████</span></li>')
    cls = "receipt flat" if flat else "receipt"
    return f"""<div class="{cls}" role="group" aria-label="{e(head_title)}">
<div class="r-head"><b><span class="f">Fraud</span>Bad</b>{e(head_title)}{('<br>'+e(head_sub)) if head_sub else ''}</div>
<ol class="r-lines">{''.join(lis)}</ol>
<div class="r-foot"><span>{e(foot[0])}</span><span>{e(foot[1])}</span></div>
<div class="stamp" aria-hidden="true">{e(stamp)}</div>
</div>"""


def type_chip(t):
    return f'<span class="ty ty-{t}" title="{e(TYPES[t][1])}">{e(TYPES[t][0])}</span>'


def tier_chip(t):
    return f'<span class="tier t-{t}" title="{e(TIERS[t][1])}">{e(TIERS[t][0])}</span>'


def card(c):
    return f"""<a class="card card-{c['type']}" href="/{c['slug']}" data-level="{c['level']}" data-type="{c['type']}" data-tier="{c['tier']}">
<div class="card-top">{type_chip(c['type'])}<span class="lvl">{LEVELS[c['level']]} · {e(c['place'])}</span></div>
<div class="card-fig">{e(c['fig'])}<small>{e(c['scale'])}</small></div>
<h3>{e(c['title'])}</h3>
<div class="card-place">{tier_chip(c['tier'])}</div>
<span class="card-go">Open the receipt →</span>
</a>"""


ORG_LD = {"@context": "https://schema.org", "@type": "Organization", "name": "FraudBad", "url": SITE,
          "logo": SITE + "/icon-512.png", "sameAs": [u for _, u in SOCIALS]}


SIGN_BASE = CTA_URL.split("#")[0]


def page_slug(path):
    """The case/page tag carried on every Sign link: index.html -> home, program/x.html -> program-x."""
    s = path[:-5] if path.endswith(".html") else path
    return "home" if s == "index" else s.replace("/", "-")


def tag_sign_links(path, text):
    slug = page_slug(path)
    for pos in ("nav", "band", "footer", "inline", "bar"):
        text = text.replace(f"__SIGN_{pos}__", f"{SIGN_BASE}?ref=fraudbad&amp;case={slug}&amp;pos={pos}#sign")
    # Gate (plan item 0.2): every link to the signing page must say where it came from.
    for m in re.finditer(r'href="(https://america\.co/receipts-act[^"]*#sign)"', text):
        if "ref=fraudbad" not in m.group(1) or "case=" not in m.group(1):
            raise SystemExit(f"untagged Sign link in {path}: {m.group(1)}")
    if "__SIGN_" in text:
        raise SystemExit(f"unknown Sign placeholder in {path}")
    return text


def write(path, text):
    if path.endswith(".html"):
        text = tag_sign_links(path, text)
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------- home
def build_home():
    counts = {k: sum(1 for c in CASES if c["level"] == k) for k in LEVELS}
    tcounts = {k: sum(1 for c in CASES if c["type"] == k) for k in TYPES}
    hero_lines = [
        ("Federal spending, FY2026", "$7,395,799,983,313", "mts"),
        ("Lost to fraud each year (GAO est.)", "$233B–$521B", "gao_fraud"),
        ("Paid in error, FY2025", "$186,000,000,000", "gao_ip"),
        ("Pentagon audits passed", "0 of 8", "dn_audit"),
        ("Grant dollars with no local trail", "74%", "pogo"),
    ]
    stats = [
        ("$186B", "paid in error by federal agencies in fiscal 2025", "gao_ip"),
        ("0 for 8", "Pentagon financial audits passed since 2018", "dn_audit"),
        ("74%", "of federal grant dollars can't be traced to a local place", "pogo"),
        (f"${M.CUM/1e12:.2f}T", f"paid wrong or without proof since {M.FIRST_YEAR} — the soft fraud nobody adds up", "pa_data"),
    ]
    stat_html = "".join(
        f'<div class="stat"><b>{e(n)}</b><p>{e(t)}</p><span class="src"><a href="{e(S[sid][3])}" rel="noopener">{e(S[sid][1])}, {e(S[sid][2])}</a></span></div>'
        for n, t, sid in stats)
    mini = ['<div></div>'] + [f'<div class="mh">{DIVE[c]["label"]}<span>{e(DIVE[c]["sub"])}</span></div>' for c in ("federal", "state", "local")]
    first_dark = {}
    for c in ("federal", "state", "local"):
        for i, (rk, _, _) in enumerate(DIVE_ROWS):
            if DIVE[c]["cells"][rk][0] == "dark":
                first_dark[c] = i; break
    for i, (rk, rl, _) in enumerate(DIVE_ROWS):
        mini.append(f'<div class="ml">{e(rl)}</div>')
        for c in ("federal", "state", "local"):
            stt = DIVE[c]["cells"][rk][0]
            fd = " first" if first_dark.get(c) == i else ""
            mini.append(f'<div class="mc {stt}{fd}">{ {"open":"Visible","partial":"Partly","dark":"Dark"}[stt] }</div>')
    mini_html = "".join(mini)
    cards = "\n".join(card(c) for c in ORDERED)
    soft_tiles = "".join(f'<a class="big" href="/{slug}"><b>{e(n)}</b><span>{e(t)}</span><i class="src">{e(S[sid][1])}</i></a>' for n, t, slug, sid in SOFT_BIG)
    legend = "".join(f'<div style="display:flex;gap:8px;align-items:center">{tier_chip(t)}<span class="t">{e(TIERS[t][1].split(".")[0])}.</span></div>' for t in TIERS)
    ld = [ORG_LD,
          {"@context": "https://schema.org", "@type": "WebSite", "name": "FraudBad", "url": SITE,
           "description": "Every major case of federal, state and local fraud, sourced, and a map of where public spending records stop."},
          {"@context": "https://schema.org", "@type": "ItemList", "name": "Mega-fraud cases",
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/{c['slug']}", "name": c["title"]} for i, c in enumerate(ORDERED)]}]
    title = "FraudBad: up to $521 billion a year lost to fraud. Here's every big case."
    desc = "Every major fraud case in federal, state and local spending, sourced to auditors, inspectors general and courts — and a map of where the receipts stop."
    body = f"""{header('cases')}
<main id="main">
<section class="hero"><div class="wrap">
<div>
<p class="kicker">No taxation without receipts</p>
<h1>$233–521 billion<span class="u">lost to fraud every year</span></h1>
<p class="lede">That's the federal government's own estimate. Below is every case big enough to matter — sourced to the auditors, inspectors general and courts that found it — and a map of where the receipts stop.</p>
<p class="soft-line">And that only counts the crimes. <a href="/soft-fraud">Soft fraud</a> — paying without proof, overpaying, paying twice, never collecting — runs into the trillions.</p>
<div class="actions"><a class="btn" href="#cases">See every case ↓</a><a class="btn ghost" href="/soft-fraud">Soft fraud →</a><a class="btn ghost" href="/transparency">Where the receipts stop →</a></div>
<div class="ticker" data-ticker aria-live="off"><span>Since you opened this page, at GAO's estimated rate</span><b>$0–$0</b><span>Based on GAO's estimate of $233B–$521B a year (2018–2022 data)</span></div>
</div>
{receipt(hero_lines, ("Itemized receipt", "NOT AVAILABLE"), "Federal spending", "Fiscal year 2026", link_mode="direct")}
</div></section>
<section class="stats" aria-label="Key numbers"><div class="wrap">{stat_html}</div></section>
<section class="sec" id="cases"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">{len(CASES)} cases</p><h2>The cases</h2></div>
<p>Every case here was found by an auditor, an inspector general, a prosecutor, a court or the agency that paid the money. Each page shows the numbers, where they came from, and how sure anyone can be.</p></div>
<div class="filterbar">
<div class="filters" role="group" aria-label="Filter by kind">
<button class="chip" data-group="type" data-filter="all" aria-pressed="true">All<span class="c">{len(CASES)}</span></button>
<button class="chip" data-group="type" data-filter="hard" aria-pressed="false">Hard fraud<span class="c">{tcounts['hard']}</span></button>
<button class="chip" data-group="type" data-filter="soft" aria-pressed="false">Soft fraud<span class="c">{tcounts['soft']}</span></button>
</div>
<div class="filters" role="group" aria-label="Filter by level">
<button class="chip" data-group="level" data-filter="all" aria-pressed="true">Every level</button>
<button class="chip" data-group="level" data-filter="federal" aria-pressed="false">Federal<span class="c">{counts['federal']}</span></button>
<button class="chip" data-group="level" data-filter="state" aria-pressed="false">State<span class="c">{counts['state']}</span></button>
<button class="chip" data-group="level" data-filter="local" aria-pressed="false">Local<span class="c">{counts['local']}</span></button>
</div></div>
<div class="grid" style="margin-top:22px">{cards}</div>
<div class="legend" aria-label="How sure we are">{legend}</div>
</div></section>
<section class="sec soft-teaser" aria-labelledby="soft-h"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:#ff4438">Bigger than the crimes</p><h2 id="soft-h">Soft fraud</h2></div>
<p>Money lost without anyone breaking a law: paid without proof, paid too much, paid twice, lost track of, or never collected. Each of these is an official or peer-reviewed number.</p></div>
<div class="big-grid">{soft_tiles}</div>
<p style="margin-top:26px"><a class="btn" href="/soft-fraud">How we search for soft fraud →</a></p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Federal · State · Local</p><h2>Where the receipts stop</h2></div>
<p>You can see the total. Follow a dollar down and the trail goes dark: who got paid next, what was bought, and whether it ever showed up.</p></div>
<div class="mini" role="table" aria-label="How far you can follow a public dollar">{mini_html}</div>
<p style="margin-top:26px"><a class="btn ink" href="/transparency">See the full map →</a></p>
</div></section>
</main>
{cta()}{footer()}"""
    write("index.html", head(title, desc, "/", "og-home.png", ld) + body)


# ---------------------------------------------------------------- case pages
def build_case(i, c):
    srcmap = {sid: n + 1 for n, sid in enumerate(c["sources"])}
    prev_c = ORDERED[i - 1] if i > 0 else ORDERED[-1]
    next_c = ORDERED[(i + 1) % len(ORDERED)]
    url = f"{SITE}/{c['slug']}"
    title = f"{c['fig']} {c['scale']}: {c['title']} | FraudBad"
    desc = c["dek"]
    happened = "".join(f"<p>{e(p)}</p>" for p in c["happened"])
    missed = "".join(f"<li>{e(m)}</li>" for m in c["missed"])
    sources = "".join(
        f'<li id="s-{srcmap[sid]}"><div><a href="{e(S[sid][3])}" rel="noopener">{e(S[sid][0])}</a><span class="src">{e(S[sid][1])} · {e(S[sid][2])}</span></div></li>'
        for sid in c["sources"])
    tweet = f"{c['fig']} {c['scale']}: {c['title']}. Want to stop it? Sign the Receipts Act."
    x_url = "https://x.com/intent/post?" + urllib.parse.urlencode({"text": tweet, "url": url})
    ld = [ORG_LD,
          {"@context": "https://schema.org", "@type": "Article", "headline": f"{c['fig']} {c['scale']}: {c['title']}",
           "description": desc, "url": url, "datePublished": UPDATED, "dateModified": UPDATED,
           "image": f"{SITE}/og-{c['slug']}.png", "author": {"@type": "Organization", "name": "FraudBad", "url": SITE},
           "publisher": {"@type": "Organization", "name": "FraudBad", "logo": {"@type": "ImageObject", "url": SITE + "/icon-512.png"}},
           "citation": [S[s][3] for s in c["sources"]], "isAccessibleForFree": True},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Cases", "item": SITE + "/#cases"},
              {"@type": "ListItem", "position": 2, "name": LEVELS[c["level"]], "item": SITE + "/#" + c["level"]},
              {"@type": "ListItem", "position": 3, "name": c["title"], "item": url}]}]
    body = f"""{header()}
<main id="main">
<section class="case-hero"><div class="wrap">
<div>
<p class="crumbs"><a href="/#cases">All cases</a> / <a href="/#{c['level']}">{LEVELS[c['level']]}</a> / {e(c['place'])}</p>
<div class="tags">{type_chip(c['type'])}<span class="lvl">{LEVELS[c['level']]} · {e(c['place'])}</span>{tier_chip(c['tier'])}</div>
<p class="fig" aria-hidden="true">{e(c['fig'])}<small>{e(c['scale'])}</small></p>
<h1><span class="sr">{e(c['fig'])} {e(c['scale'])}: </span>{e(c['title'])}</h1>
<p class="lede">{e(c['dek'])}</p>
</div>
{receipt(c['receipt'], c['redact'], 'Public receipt', c['place'], stamp=STAMP[c['tier']], srcmap=srcmap)}
</div></section>
<section class="sec case-body"><div class="wrap">
<div>
<section><h2>What happened</h2>{happened}</section>
<section><h2>Why nobody caught it</h2><ul>{missed}</ul></section>
<section><h2>How sure are we?</h2><div class="sure">{tier_chip(c['tier'])}<p><strong>{e(TIERS[c['tier']][1])}</strong></p><p style="margin:0">{e(c['sure'])}</p></div></section>
<section><h2>Sources</h2><ol class="sources">{sources}</ol><p class="src" style="margin-top:14px">Spot an error? <a href="https://america.co/work-with-us">Send the source</a> and we'll fix it.</p></section>
</div>
<aside class="aside-card" aria-label="Share and act">
<div class="receipt flat static" style="padding:20px">
<p class="kicker" style="color:var(--red);margin-bottom:8px">Want to stop it?</p>
<p style="font:400 30px/1 var(--display);text-transform:uppercase;margin:0 0 14px">Sign the Receipts Act.</p>
<a class="btn" href="__SIGN_inline__">Sign it on America.co ↗</a>
</div>
<div class="share"><button class="btn ink sm" data-copy="{url}">Copy link</button><a class="btn ink sm" href="{e(x_url)}" rel="noopener">Post on X</a><button class="btn ink sm" data-share="{url}">Share</button><p class="status" aria-live="polite"></p></div>
{__import__("pages_more").embed_snippet(__import__("sys").modules[__name__], c)}
</aside>
</div>
<div class="wrap"><nav class="pager" aria-label="More cases"><a href="/{prev_c['slug']}"><span class="k">← Previous case</span><b>{e(prev_c['fig'])} {e(prev_c['scale'])}: {e(prev_c['title'])}</b></a><a class="next" href="/{next_c['slug']}"><span class="k">Next case →</span><b>{e(next_c['fig'])} {e(next_c['scale'])}: {e(next_c['title'])}</b></a></nav></div>
</section>
</main>
{cta()}{footer()}"""
    write(f"{c['slug']}.html", head(title, desc, f"/{c['slug']}", f"og-{c['slug']}.png", ld) + body)


# ---------------------------------------------------------------- transparency
def build_transparency():
    st_label = {"open": "Visible", "partial": "Partly", "dark": "Dark"}
    cells = ['<div class="corner"></div>']
    for col in ("federal", "state", "local"):
        cells.append(f'<div class="colhead" data-col="{col}" style="--o:{(("federal","state","local").index(col)+1)*100}"><b>{DIVE[col]["label"]}</b><span>{e(DIVE[col]["sub"])}</span></div>')
    stops = {}
    for col in ("federal", "state", "local"):
        for i, (rk, _, _) in enumerate(DIVE_ROWS):
            if DIVE[col]["cells"][rk][0] == "dark":
                stops[col] = i
                break
    # grid order: row by row; on mobile CSS stacks, so we also emit an order-friendly structure via 'order'
    for i, (rk, rl, rs) in enumerate(DIVE_ROWS):
        cells.append(f'<div class="rowhead"><i>{i+1:02d}</i><b>{e(rl)}</b><span>{e(rs)}</span></div>')
        for ci, col in enumerate(("federal", "state", "local")):
            st, txt, sid = DIVE[col]["cells"][rk]
            stop = " stop" if stops.get(col) == i else ""
            src = f'<span class="src"><a href="{e(S[sid][3])}" rel="noopener">{e(S[sid][1])}, {e(S[sid][2])}</a></span>' if sid else ""
            order = (ci + 1) * 100 + i + 1
            cells.append(f'<div class="cell {st}{stop}" data-col="{col}" data-row="{i}" style="--o:{order}"><span class="rh-label">{e(rl)}</span><span class="st">{st_label[st]}</span><div>{e(txt)}</div>{src}</div>')
    dive = "\n".join(cells)
    dm = []
    for big, unit, txt, sids in DARK_MONEY:
        sids = sids if isinstance(sids, list) else [sids]
        srcs = " · ".join(f'<a href="{e(S[s][3])}" rel="noopener">{e(S[s][1])}</a>' for s in sids)
        dm.append(f'<div class="dm"><b>{e(big)}</b><em>{e(unit)}</em><div class="bars" aria-hidden="true"><i style="width:92%"></i><i style="width:74%"></i><i style="width:85%"></i></div><p>{e(txt)}</p><span class="src">{srcs}</span></div>')
    bars = "".join(f'<div class="bar-row" style="--w:{pct}%"><span>{e(t)}</span><span class="track" role="img" aria-label="{pct}% of {total:,} have no website listed"><span class="fill"></span></span><b>{pct:.0f}%</b></div>' for t, total, nw, pct in LOCAL_TYPES)
    soap_lines = [
        ("Item", "Hand soap dispenser, C-17", "dodig"),
        ("Markup over commercial price", "7,943%", "mil_soap"),
        ("Overpaid on the dispensers", "$149,072", "mil_soap"),
        ("Parts the Air Force overpaid for", "12 of 46", "mil_soap"),
        ("Parts it couldn't tell if the price was fair", "25 of 46", "mil_soap"),
    ]
    title = "Where the receipts stop: the limits of federal, state and city spending transparency | FraudBad"
    desc = "Follow a public dollar down and the records run out. 74% of federal grant dollars can't be traced to a local place; most subawards go unreported; 56% of local governments list no website."
    ld = [ORG_LD, {"@context": "https://schema.org", "@type": "Article", "headline": "Where the receipts stop", "description": desc,
                   "url": SITE + "/transparency", "datePublished": UPDATED, "dateModified": UPDATED, "image": SITE + "/og-transparency.png",
                   "author": {"@type": "Organization", "name": "FraudBad"}, "citation": sorted({S[d[2]][3] for c in DIVE.values() for d in c["cells"].values() if d[2]})}]
    soap_srcmap = None
    body = f"""{header('transparency')}
<main id="main">
<section class="page-hero"><div class="wrap">
<p class="kicker" style="color:var(--red)">Federal · State · Local</p>
<h1>You can see the total.<br>You can't see the receipt.</h1>
<p class="lede">Every level of government publishes how much it spends. Follow a single dollar down — to who got it, who they paid next, what was bought and whether it showed up — and the records run out. Here's exactly where.</p>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Follow one dollar down</p><h2>The trail, level by level</h2></div>
<div class="legend" style="margin:0"><span class="tier" style="background:var(--navy);color:#fff">Visible</span><span class="t">Public and usable</span><span class="tier" style="background:#fff;box-shadow:inset 0 0 0 1.5px var(--ink)">Partly</span><span class="t">Gaps or delays</span><span class="tier" style="background:var(--red);color:#fff">Dark</span><span class="t">No public record</span></div></div>
<div class="dive">{dive}</div>
</div></section>
<section class="sec" style="background:var(--paper-2)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">No receipt by design</p><h2>Money you can't follow at all</h2></div><p>Some spending never had a trail to begin with.</p></div>
<div class="dark-money">{''.join(dm)}</div>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Local governments, 2026</p><h2>91,729 governments. 51,813 with no website on file.</h2></div>
<p>Counted from the Census Bureau's 2026 list of every county, city, township, special district and school district. Share with no website listed:</p></div>
<div class="bars-chart">{bars}</div>
<p class="src" style="margin-top:16px">Source: <a href="{e(S['census'][3])}">{e(S['census'][1])}, {e(S['census'][0])}</a>. "No website listed" means the Census directory has none on file for that government.</p>
</div></section>
<section class="sec" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap soap">
<div>{receipt(soap_lines, ("What a fair price was, by law", "REDACTED IN REPORT"), "One receipt", "U.S. Air Force · C-17 spare parts", stamp="7,943%", link_mode="direct")}</div>
<div>
<p class="kicker" style="color:var(--red)">What one receipt shows</p>
<h2>The $149,072 soap dispensers</h2>
<p class="lede" style="margin-top:16px">When the Pentagon's inspector general compared what the Air Force paid for 46 spare parts against what they should cost, it found a soap dispenser marked up 7,943%. For 25 of the 46 parts, the Air Force couldn't even say whether the price was fair.</p>
<p>Nobody needed an investigation to see it. They needed the price paid next to what everyone else pays. The RECEIPTS Act would make that kind of comparison public, starting with federal orders over $25,000 placed through GSA's schedules.</p>
<p><a class="btn" href="__SIGN_inline__">Sign the Receipts Act ↗</a></p>
</div>
</div></section>
</main>
{cta()}{footer()}"""
    write("transparency.html", head(title, desc, "/transparency", "og-transparency.png", ld) + body)


def build_soft():
    big = "".join(f'<a class="big" href="/{slug}"><b>{e(n)}</b><span>{e(t)}</span><i class="src">{e(S[sid][1])}, {e(S[sid][2])}</i></a>' for n, t, slug, sid in SOFT_BIG)
    by = {c["slug"]: c for c in CASES}
    sig = []
    for num, name, what, where, measure, ex in SIGNALS:
        exl = "".join(f'<a href="/{x}">{e(by[x]["fig"])} {e(by[x]["scale"])}: {e(by[x]["title"])} →</a>' for x in ex)
        sig.append(f'<article class="sig"><i>{num}</i><h3>{e(name)}</h3><p class="what">{e(what)}</p><dl><dt>Where we look</dt><dd>{e(where)}</dd><dt>What we measure</dt><dd>{e(measure)}</dd></dl>{("<div class=ex>"+exl+"</div>") if exl else ""}</article>')
    def rows(items):
        out = []
        for f in items:
            d = f["desc"] if f["desc"] else "(blank)"
            amt = "${:,.2f}B".format(f["amount"] / 1e9)
            rec = f["recipient"].title()
            ag = f["agency"].replace("Department of ", "")
            out.append(f'<tr><td class="num">{e(amt)}</td><td>{e(rec)}</td><td>{e(ag)}</td><td class="mono">{e(d[:60])}</td><td><a href="{e(f["url"])}" rel="noopener">Award ↗</a></td></tr>')
        return "".join(out)
    soft_cases = "\n".join(card(c) for c in ORDERED if c["type"] == "soft")
    title = "Soft fraud: the trillions lost to negligence, and how we search for it | FraudBad"
    desc = f"Paying without proof, overpaying, paying twice, losing track, never collecting. ${M.CUM/1e12:.2f} trillion in improper payments since {M.FIRST_YEAR} is just the start. Here's every official number and the seven signals we use to find more."
    ld = [ORG_LD, {"@context": "https://schema.org", "@type": "Article", "headline": "Soft fraud", "description": desc, "url": SITE + "/soft-fraud",
                   "datePublished": UPDATED, "dateModified": UPDATED, "image": SITE + "/og-soft-fraud.png", "author": {"@type": "Organization", "name": "FraudBad"}}]
    body = f"""{header('soft')}
<main id="main">
<section class="page-hero"><div class="wrap">
<p class="kicker" style="color:#ff4438">Bigger than the crimes</p>
<h1>Soft fraud</h1>
<p class="lede">Hard fraud is someone stealing. Soft fraud is everyone shrugging: money paid without proof, paid too much, paid twice, lost track of, or never collected. No one has to break a law, so no one gets charged — and it runs into the trillions.</p>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Official numbers</p><h2>The soft-fraud receipt</h2></div>
<p>Each figure comes from GAO, the IRS, Congress's Medicare advisers, a peer-reviewed study, or the government's own spending data. We don't add them together: they overlap and measure different things.</p></div>
<div class="big-grid">{big}</div>
</div></section>
<section class="sec" id="search" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">The method</p><h2>How we search for soft fraud</h2></div>
<p>Seven signals. Each one names where to look and what to measure, so anyone can repeat the search and check our work.</p></div>
<div class="sigs">{''.join(sig)}</div>
</div></section>
<section class="sec" id="contracts"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Signal 06, run live</p><h2>The biggest contracts with no explanation</h2></div>
<p>We pulled the 100 largest federal contracts with spending activity in fiscal 2026 from USAspending.gov — worth {e(f"${TOP_TOTAL/1e9:,.1f}B")} together — and checked what each one says it's for.</p></div>
<h3 class="tbl-h">Blank, or only a filing code: {len(BLANK)} contracts, {e(f"${BLANK_TOTAL/1e9:,.1f}B")}</h3>
<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Award value</th><th>Recipient</th><th>Agency</th><th>Published description</th><th></th></tr></thead><tbody>{rows(BLANK)}</tbody></table></div>
<h3 class="tbl-h">Three words or fewer: {len(SHORT)} more, {e(f"${SHORT_TOTAL/1e9:,.1f}B")}</h3>
<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Award value</th><th>Recipient</th><th>Agency</th><th>Published description</th><th></th></tr></thead><tbody>{rows(SHORT)}</tbody></table></div>
<p class="src" style="margin-top:14px">Query: {e(SIG["query"])}. Pulled {e(SIG["pulled"])}. Award values are lifetime totals for awards with any action in fiscal 2026. A blank description is not proof of waste; it means the public can't tell what was bought.</p>
</div></section>
<section class="sec" style="background:var(--paper-2)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">{sum(1 for c in CASES if c["type"]=="soft")} cases</p><h2>Every soft-fraud case</h2></div></div>
<div class="grid">{soft_cases}</div>
</div></section>
</main>
{cta()}{footer()}"""
    write("soft-fraud.html", head(title, desc, "/soft-fraud", "og-soft-fraud.png", ld) + body)


# ---------------------------------------------------------------- ledger (official improper-payment dataset)
def build_ledger():
    pa = json.load(open(os.path.join(os.path.dirname(__file__), "data", "paymentaccuracy_fy2025.json")))
    dnr = [p for p in pa["programs"] if p["raw_outlays"] == "Did not report"]
    yrs = sorted(M.YEARS)
    top = max(M.YEARS[y]["amount_m"] for y in yrs)
    peak = max(yrs, key=lambda y: M.YEARS[y]["amount_m"])
    keep = {yrs[0], peak, yrs[-1]}
    bars = "".join(
        f'<a class="y{" hi" if y in keep else ""}" href="/year/{y}" style="--h:{M.YEARS[y]["amount_m"]/top*100:.1f}%" title="FY{y}: ${M.YEARS[y]["amount_m"]/1000:,.1f} billion across {M.YEARS[y]["programs"]} programs">'
        + (f'<b>${M.YEARS[y]["amount_m"]/1000:,.0f}B</b>' if y in keep else "") + '</a>' for y in yrs)
    shown = set(keep) | {y for y in yrs if y % 5 == 0 and all(abs(y - k) >= 3 for k in keep)}
    xl = "".join(f'<span{" class=k" if y in shown else ""}>{str(y)[2:] if y not in keep else y}</span>' for y in yrs)
    def money(m):
        if m >= 1000: return f"${m/1000:,.2f}B" if m < 10000 else f"${m/1000:,.1f}B"
        return f"${m:,.0f}M" if m >= 1 else "<$1M"
    rc = [("Data existed and was accessible — nobody checked it", M.RC_FAIL), ("The data needed didn't exist", M.RC_NOEXIST),
          ("Not enough paperwork to tell either way", M.RC_DOCS), ("Data existed, but the agency couldn't get it", M.RC_INAB),
          ("Right amount, but the rules weren't followed", M.RC_TECH)]
    rcmax = max(v for _, v in rc)
    rc_html = "".join(f'<div class="bar-row"><span>{e(lab)}</span><div class="track"><div class="fill" style="--w:{v/rcmax*100:.1f}%"></div></div><b>${v/1e9:,.1f}B</b></div>' for lab, v in rc)
    rec_y = [y for y in sorted(M.REC) if y >= 2016]
    rmax = max(M.REC[y]["identified_m"] for y in rec_y)
    rec_html = "".join(
        f'<div class="rec-y"><span class="yy">{y}</span><div class="rec-bars"><i class="flag" style="width:{M.REC[y]["identified_m"]/rmax*100:.1f}%"></i><i class="got" style="width:{M.REC[y]["recovered_m"]/rmax*100:.1f}%"></i></div><span class="vv">${M.REC[y]["recovered_m"]/1000:,.1f}B of ${M.REC[y]["identified_m"]/1000:,.1f}B</span></div>'
        for y in rec_y)
    rows = []
    for i, p in enumerate(M.PROGS, 1):
        r = p["rate"] or 0
        pr = p["prev_rate"]
        chg = ""
        if pr is not None:
            d = (r - pr) * 100
            chg = f'<span class="{"up" if d > 0.05 else ("dn" if d < -0.05 else "")}">{pr*100:.1f}%</span>'
        else:
            chg = '<span class="na" title="Not reported under this name in FY2024">—</span>'
        _k = (p["agency"], " ".join(p["program"].split()))
        _pn = f'<a href="{PROGRAM_LINKS[_k]}">{e(p["program"])}</a>' if _k in PROGRAM_LINKS else e(p["program"])
        import pages_more as _pm
        rows.append(f'<tr><td class="rk">{i}</td><td><b>{_pn}</b><span class="ag"><a href="/agency/{_pm.agency_slug(p["agency"])}">{e(M.agency(p["agency"]))}</a></span></td>'
                    f'<td class="num">{money(p["outlays_m"])}</td><td class="num">{money(p["total_m"])}</td>'
                    f'<td class="rt"><span class="rbar"><i style="width:{min(r,1)*100:.1f}%"></i></span>{r*100:.1f}%</td><td class="pv">{chg}</td></tr>')
    nc = ", ".join(M.agency(a) for a in M.NONCOMP)
    dnr_html = "".join(f'<li><b>{e(p["name"])}</b><span>{e(p["agency"])}</span></li>' for p in dnr)
    tiles = [
        (f"${M.CUM/1e12:.2f}T", f"paid wrong or without proof, FY{M.FIRST_YEAR}–FY2025", "pa_data", "#years"),
        (f"${M.FY25/1e9:,.1f}B", "in fiscal 2025 alone, across 64 programs", "pa_data", "#programs"),
        (f"${M.RC_FAIL/1e9:,.1f}B", "of it paid when the data to catch it already existed", "pa_data", "#why"),
        (f"{M.OVER10}", "programs got more than 1 in 10 dollars wrong", "pa_data", "#programs"),
        (f"${M.REC25['recovered_m']/1000:,.1f}B", f"recovered, of ${M.REC25['identified_m']/1000:,.1f}B flagged to claw back", "pa_data", "#recovery"),
        (f"{len(M.NONCOMP)} of {M.N_AGENCIES}", "agencies out of compliance with the payment-integrity law (FY2024)", "pa_data", "#law"),
    ]
    big = "".join(f'<a class="big" href="{h}"><b>{e(n)}</b><span>{e(t)}</span><i class="src">{e(S[sid][1].split(";")[0])}</i></a>' for n, t, sid, h in tiles)
    title = f"The ledger: every federal program's error rate, and ${M.CUM/1e12:.2f} trillion since {M.FIRST_YEAR} | FraudBad"
    desc = f"Every federal program that reports improper payments, from the government's own dataset: ${M.FY25/1e9:,.1f} billion paid wrong or without proof in fiscal 2025, ${M.CUM/1e12:.2f} trillion since {M.FIRST_YEAR}, and why."
    ld = [ORG_LD, {"@context": "https://schema.org", "@type": "Dataset", "name": "Federal improper payments by program, FY2004–FY2025",
                   "description": desc, "url": SITE + "/ledger", "creator": {"@type": "Organization", "name": "Office of Management and Budget"},
                   "isBasedOn": S["pa_data"][3], "dateModified": UPDATED, "license": "https://www.usa.gov/government-works"}]
    body = f"""{header('ledger')}
<main id="main">
<section class="page-hero"><div class="wrap">
<p class="kicker" style="color:#ff4438">The government's own receipt</p>
<h1>The ledger</h1>
<p class="lede">Every year, federal agencies have to measure how much they paid in the wrong amount, to the wrong person, or without the paperwork to prove it was right. They report it to the White House budget office, which publishes one spreadsheet. We read every row. Here it is.</p>
</div></section>
<section class="sec"><div class="wrap"><div class="big-grid">{big}</div></div></section>
<section class="sec" id="years" style="background:#fff;border-top:1px solid var(--rule)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">{len(yrs)} years</p><h2>Paid wrong, year by year</h2></div>
<p>Improper and unverifiable payments reported each fiscal year, all programs combined. The total through 2024 — ${M.CUM24/1e12:.2f} trillion — matches the roughly $2.8 trillion GAO reports. Fiscal 2025 takes it to ${M.CUM/1e12:.2f} trillion.</p></div>
<div class="yrs" role="img" aria-label="Bar chart of improper payments by fiscal year, from ${M.YEARS[yrs[0]]['amount_m']/1000:,.0f} billion in {yrs[0]} to a peak of ${M.YEARS[peak]['amount_m']/1000:,.0f} billion in {peak} and ${M.YEARS[yrs[-1]]['amount_m']/1000:,.0f} billion in {yrs[-1]}">{bars}</div>
<div class="yrs-x" aria-hidden="true">{xl}</div>
<p class="src" style="margin-top:14px">Source: <a href="{e(S['pa_data'][3])}" rel="noopener">PaymentAccuracy.gov FY2025 dataset</a>, "All Program Results," column "Improper Payment and Unknown Payment Amount," summed by fiscal year. Programs reporting each year range from {min(M.YEARS[y]['programs'] for y in yrs)} to {max(M.YEARS[y]['programs'] for y in yrs)}.</p>
</div></section>
<section class="sec" id="why"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Root causes, FY2025</p><h2>Why it happened</h2></div>
<p>Each program has to say why its payments went wrong, using categories the White House budget office defines. Two-thirds of the money went out wrong even though the information to stop it existed and the agency could get to it.</p></div>
<div class="bars-chart wide">{rc_html}</div>
<p class="src" style="margin-top:14px">Category definitions: <a href="{e(S['omb_m2119'][3])}" rel="noopener">OMB M-21-19, Table 3</a>. Amounts: FY2025 dataset, "Improper Payment Root Causes," summed by FraudBad (total ${sum(v for _, v in rc)/1e9:,.1f}B).</p>
</div></section>
<section class="sec" id="programs" style="background:var(--paper-2)"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">{len(M.PROGS)} programs</p><h2>Every program that reported, fiscal 2025</h2></div>
<p>Ranked by dollars paid wrong or without proof. "Rate" is the share of the program's payments. The last column is the same program's rate a year earlier.</p></div>
<div class="tbl-wrap"><table class="tbl ledger"><thead><tr><th>#</th><th>Program</th><th>Paid out</th><th>Wrong or unproven</th><th>Rate</th><th>FY2024</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="src" style="margin-top:14px">Source: <a href="{e(S['pa_data'][3])}" rel="noopener">FY2025 dataset</a>, "All Program Results," fiscal year 2025 rows. Includes improper payments and "unknown" payments the agency couldn't verify. Not all of it is fraud; each agency's own report explains its number.</p>
</div></section>
<section class="sec" id="recovery"><div class="wrap">
<div class="sec-head"><div><p class="kicker" style="color:var(--red)">Clawbacks</p><h2>How much comes back</h2></div>
<p>Overpayments agencies flagged to recover each year (full bar), and what they actually recovered (red). Recoveries in a year can include money flagged in earlier years.</p></div>
<div class="rec">{rec_html}</div>
<p class="src" style="margin-top:14px">Source: FY2025 dataset, "Rate and Amt of Recovery," summed across agencies by FraudBad.</p>
</div></section>
<section class="sec" id="law" style="background:var(--ink);color:#e8ebf2"><div class="wrap ledger-dark">
<div><p class="kicker" style="color:#ff4438">The law</p><h2 style="color:#fff">{len(M.NONCOMP)} of {M.N_AGENCIES} agencies broke it</h2>
<p>The Payment Integrity Information Act of 2019 requires agencies to measure improper payments, publish them and cut them. Inspectors general check every year. For fiscal 2024, these agencies were rated non-compliant: {e(nc)}.</p>
<p class="src">Source: FY2025 dataset, "Compliance Trend Table," fiscal 2024 column. Fiscal 2025 ratings come out in 2026's dataset.</p></div>
<div><p class="kicker" style="color:#ff4438">Not in the total</p><h2 style="color:#fff">Programs that didn't report</h2>
<ul class="dnr">{dnr_html}</ul>
<p class="src">Listed as "Did not report" for FY2025 on <a href="{e(S['pa_site'][3])}" rel="noopener" style="color:#fff">PaymentAccuracy.gov</a>. Their errors aren't in any number above.</p></div>
</div></section>
</main>
{cta()}{footer()}"""
    write("ledger.html", head(title, desc, "/ledger", "og-ledger.png", ld) + body)


# ---------------------------------------------------------------- method
def build_method():
    tiers = "".join(f'<div>{tier_chip(t)}<p style="margin:0">{e(TIERS[t][1])}</p></div>' for t in TIERS)
    used = []
    for c in CASES:
        for s in c["sources"]:
            if s not in used: used.append(s)
    for col in DIVE.values():
        for d in col["cells"].values():
            if d[2] and d[2] not in used: used.append(d[2])
    for d in DARK_MONEY:
        for s in (d[3] if isinstance(d[3], list) else [d[3]]):
            if s not in used: used.append(s)
    for s in ("census", "dodig", "mil_soap", "receipts_act", "pa_data", "pa_site", "omb_m2119", "gao_cfs"):
        if s not in used: used.append(s)
    srcs = "".join(f'<li><div><a href="{e(S[s][3])}" rel="noopener">{e(S[s][0])}</a><span class="src">{e(S[s][1])} · {e(S[s][2])}</span></div></li>' for s in used)
    title = "How FraudBad judges cases | FraudBad"
    desc = "How cases make the list, what each evidence label means, what an improper payment is, and every source behind the site."
    body = f"""{header('method')}
<main id="main">
<section class="page-hero"><div class="wrap"><p class="kicker" style="color:var(--red)">Method</p><h1>How we judge</h1>
<p class="lede">No invented numbers. No guesses dressed up as facts. Every figure on this site comes from an auditor, an inspector general, a prosecutor, a court or the agency that paid the money — and every page says which.</p></div></section>
<section class="sec"><div class="wrap prose">
<h2>How a case makes the list</h2>
<p>A case is listed when an official body has put a dollar figure on fraud, likely fraud, or payments nobody can prove were right, and the amount runs to hundreds of millions of dollars or more. That body can be the Government Accountability Office, an inspector general, a state auditor or comptroller, the Justice Department, a court, or the agency itself.</p>
<p>News reports are used to show what officials said and when. Wherever we could, we link to the official document itself.</p>
<h2>Hard fraud and soft fraud</h2>
<p><strong>Hard fraud</strong> is theft and deception: schemes, crimes, and official estimates of fraud. <strong>Soft fraud</strong> is negligence: money paid without proof, paid too much, paid twice, lost track of, or never collected. Nobody has to break a law for soft fraud to happen, and nobody gets charged — which is why it's bigger. <a href="/soft-fraud#search">Here's exactly how we search for it.</a></p>
<h2>How sure are we?</h2>
<p>Every case carries one label. It tells you what kind of number you're looking at.</p>
<div class="tier-list">{tiers}</div>
<h2>Fraud is not the same as an improper payment</h2>
<p>An improper payment is money paid in the wrong amount, to the wrong person, or without the records to prove it was right. Some improper payments are fraud. Many are mistakes. A large share are payments where the paperwork simply isn't there.</p>
<p>That last kind is the reason this site exists. When a payment has no receipt, nobody can tell honest error from theft. The government's own estimate of fraud — $233 billion to $521 billion a year — is bigger than its yearly improper-payment total, because most fraud is never caught.</p>
<h2>What we won't do</h2>
<p>We won't name people who haven't been charged. We won't call a charge a conviction. We won't claim the RECEIPTS Act covers programs it doesn't: as drafted, it starts with federal orders over $25,000 placed through GSA's schedules.</p>
<h2>Corrections</h2>
<p>Found a number that's wrong or out of date? <a href="https://america.co/work-with-us">Send us the source</a>. We fix errors and note the date.</p>
<h2 id="sources">Every source on this site</h2>
<ol class="sources">{srcs}</ol>
</div></section>
</main>
{cta()}{footer()}"""
    write("method.html", head(title, desc, "/method", "og-home.png", [ORG_LD]) + body)


def build_404():
    body = f"""{header()}
<main id="main"><section class="page-hero"><div class="wrap"><p class="kicker" style="color:var(--red)">404</p><h1>No receipt for this page.</h1>
<p class="lede">It may have moved. Every case is listed on the home page.</p><p style="margin-top:24px"><a class="btn" href="/#cases">See every case</a></p></div></section></main>
{cta()}{footer()}"""
    write("404.html", head("Page not found | FraudBad", "This page doesn't exist.", "/404", "og-home.png").replace('content="index,follow,max-image-preview:large"', 'content="noindex"') + body)


def build_meta():
    urls = ["/", "/soft-fraud", "/ledger", "/transparency", "/method"] + [f"/{c['slug']}" for c in ORDERED] + EXTRA_URLS
    sm = "".join(f"<url><loc>{SITE}{u if u!='/' else '/'}</loc><lastmod>{UPDATED}</lastmod></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    write("CNAME", "fraudbad.com\n")
    write(GSC_FILE, f"google-site-verification: {GSC_FILE}")
    write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    write(".nojekyll", "")
    write("site.webmanifest", json.dumps({"name": "FraudBad", "short_name": "FraudBad", "start_url": "/", "display": "standalone",
                                          "background_color": "#0a1f44", "theme_color": "#0a1f44",
                                          "icons": [{"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
                                                    {"src": "/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}]}))


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in ("site.css", "site.js", "favicon.svg", "anton-latin.woff2", "plexmono-400-latin.woff2", "plexmono-600-latin.woff2", "publicsans-var-latin.woff2"):
        if os.path.exists(os.path.join(ASSETS, f)):
            shutil.copy(os.path.join(ASSETS, f), os.path.join(OUT, f))
    for f in os.listdir(os.path.join(OUT, "fonts")) if os.path.isdir(os.path.join(OUT, "fonts")) else []:
        shutil.move(os.path.join(OUT, "fonts", f), os.path.join(OUT, f))
    if os.path.isdir(os.path.join(OUT, "fonts")):
        os.rmdir(os.path.join(OUT, "fonts"))
    build_home()
    for i, c in enumerate(ORDERED):
        build_case(i, c)
    build_transparency()
    build_soft()
    import pages_more
    pages_more.data()
    PROGRAM_LINKS.update(pages_more.data()["links"])
    build_ledger()
    build_method()
    import content_soft as _cs, content_more as _cm, sys as _sys
    added = {c["slug"]: "2026-11-09" for c in _cs.NEW_SOFT + _cm.NEW}
    pages_more.build_all(_sys.modules[__name__], added)
    build_404()
    build_meta()
    print("built", len(os.listdir(OUT)), "files")


if __name__ == "__main__":
    main()
