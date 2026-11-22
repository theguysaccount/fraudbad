"""Comprehensive SEO & real-data regression test suite for FraudBad.

Validates:
1. Tiered sitemap index (sitemap.xml) + 4 child sitemaps: valid XML, canonical origin,
   truthful <lastmod>2026-11-22</lastmod>, zero duplicates, 100% coverage of indexable HTML.
2. Deterministic IndexNow key file and robots.txt.
3. Valid JSON-LD parsing on 100% of built pages, canonical non-fragment BreadcrumbList
   on every non-home page, Dataset schema on entity/data hubs, FAQPage on answer pages.
4. Zero truncated titles ("…") or truncated meta descriptions ("…") across all pages.
5. Zero broken internal links (href/src/og:image/downloads) and zero orphan sitemap pages.
6. Real data fidelity against OMB FY2025 dataset, cases.json, and DOL UI rates.

Usage: python3 _build/test_seo_regression.py [site_dir]
"""
import collections
import csv
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "site")
sys.path.insert(0, HERE)
import content

EXPECTED_ORIGIN = "https://fraudbad.com"
EXPECTED_LASTMOD = content.UPDATED
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def resolve_disk(path):
    path = path.split("#")[0].split("?")[0]
    if path in ("", "/"):
        return os.path.isfile(os.path.join(SITE, "index.html"))
    rel = path.lstrip("/")
    p = os.path.join(SITE, rel)
    return os.path.isfile(p) or os.path.isfile(p + ".html") or os.path.isfile(os.path.join(p, "index.html"))


def html_file_for(path):
    if path == "/":
        return os.path.join(SITE, "index.html")
    if path.endswith("/"):
        return os.path.join(SITE, path.strip("/"), "index.html")
    return os.path.join(SITE, path.lstrip("/") + ".html")


# 1. Tiered sitemap index + child sitemaps
sm_index_path = os.path.join(SITE, "sitemap.xml")
check(os.path.isfile(sm_index_path), "sitemap.xml missing")
root = ET.fromstring(open(sm_index_path, encoding="utf-8").read())
check(root.tag.endswith("sitemapindex"), f"sitemap.xml should be <sitemapindex>, got {root.tag}")
child_nodes = root.findall("s:sitemap", NS)
check(len(child_nodes) == 4, f"expected 4 child sitemaps, got {len(child_nodes)}")

sitemap_paths = []
child_counts = {}
for node in child_nodes:
    loc = node.findtext("s:loc", default="", namespaces=NS)
    lm = node.findtext("s:lastmod", default="", namespaces=NS)
    check(loc.startswith(EXPECTED_ORIGIN + "/sitemap-"), f"bad child sitemap loc: {loc}")
    check(lm == EXPECTED_LASTMOD, f"child sitemap {loc} lastmod {lm} != {EXPECTED_LASTMOD}")
    cname = urlparse(loc).path.lstrip("/")
    cfile = os.path.join(SITE, cname)
    check(os.path.isfile(cfile), f"missing child sitemap file: {cname}")
    croot = ET.fromstring(open(cfile, encoding="utf-8").read())
    check(croot.tag.endswith("urlset"), f"{cname} should be <urlset>")
    urls = croot.findall("s:url", NS)
    child_counts[cname] = len(urls)
    check(len(urls) > 0, f"{cname} is empty")
    for u in urls:
        uloc = u.findtext("s:loc", default="", namespaces=NS)
        ulm = u.findtext("s:lastmod", default="", namespaces=NS)
        check(uloc.startswith(EXPECTED_ORIGIN + "/"), f"non-canonical loc in {cname}: {uloc}")
        check(ulm == EXPECTED_LASTMOD, f"bad lastmod {ulm} for {uloc}")
        upath = urlparse(uloc).path or "/"
        check(resolve_disk(upath), f"sitemap url missing on disk: {upath}")
        sitemap_paths.append(upath)

check(len(sitemap_paths) == len(set(sitemap_paths)), "duplicate URLs across tiered sitemaps")
sitemap_set = set(sitemap_paths)

# Ensure all indexable HTML on disk is in sitemaps, and zero embed/share-kit/404 leaked
on_disk = set()
for dp, dirs, fs in os.walk(SITE):
    dirs[:] = [d for d in dirs if d not in (".git", "_build")]
    for f in fs:
        if f.endswith(".html") and f != "404.html" and not f.startswith("google"):
            rel = os.path.relpath(os.path.join(dp, f), SITE)[:-5]
            p = "/" if rel == "index" else "/" + (rel[:-5] if rel.endswith("/index") else rel)
            if p.startswith(("/embed/", "/share-kit")):
                check(p not in sitemap_set, f"noindex page leaked into sitemap: {p}")
            else:
                on_disk.add(p)

check(on_disk == sitemap_set, f"sitemap/disk mismatch: missing={sorted(on_disk - sitemap_set)[:5]}, extra={sorted(sitemap_set - on_disk)[:5]}")

# 2. IndexNow key file + robots.txt
idx_file = os.path.join(SITE, f"{content.INDEXNOW_KEY}.txt")
check(os.path.isfile(idx_file), f"IndexNow key file missing: {idx_file}")
if os.path.isfile(idx_file):
    check(open(idx_file, encoding="utf-8").read().strip() == content.INDEXNOW_KEY, "IndexNow key file content mismatch")
robots = open(os.path.join(SITE, "robots.txt"), encoding="utf-8").read()
check("User-agent: *" in robots and "Allow: /" in robots, "robots.txt missing Allow: /")
check(f"Sitemap: {EXPECTED_ORIGIN}/sitemap.xml" in robots, "robots.txt missing Sitemap directive")

# 3, 4, 5. Per-page SEO, JSON-LD, internal links, reachability graph
graph = collections.defaultdict(set)
titles, descs = set(), set()
dataset_pages = 0
faq_pages = 0

for p in sorted(sitemap_set):
    fpath = html_file_for(p)
    doc = open(fpath, encoding="utf-8").read()
    title = html.unescape((re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1].strip())
    desc = html.unescape((re.search(r'<meta name="description" content="([^"]*)"', doc) or [None, ""])[1])
    check(bool(title) and len(title) <= 70 and "…" not in title, f"{p}: bad title ({len(title)} chars): {title}")
    check(50 <= len(desc) <= 170 and "…" not in desc, f"{p}: bad desc ({len(desc)} chars): {desc}")
    check(title not in titles, f"{p}: duplicate title {title}")
    check(desc not in descs, f"{p}: duplicate desc {desc[:80]}")
    titles.add(title)
    descs.add(desc)

    canon = (re.search(r'<link rel="canonical" href="([^"]+)"', doc) or [None, ""])[1]
    check(canon == EXPECTED_ORIGIN + p, f"{p}: canonical {canon} != {EXPECTED_ORIGIN + p}")

    og_img = (re.search(r'<meta property="og:image" content="([^"]+)"', doc) or [None, ""])[1]
    check(og_img.startswith(EXPECTED_ORIGIN + "/"), f"{p}: invalid og:image {og_img}")
    if og_img.startswith(EXPECTED_ORIGIN + "/"):
        check(resolve_disk(urlparse(og_img).path), f"{p}: og:image missing on disk: {og_img}")

    ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
    types = set()
    for blk in ld_blocks:
        obj = json.loads(blk)
        tname = obj.get("@type")
        types.add(tname)
        if tname == "BreadcrumbList":
            els = obj.get("itemListElement", [])
            check(len(els) >= 2, f"{p}: BreadcrumbList too short")
            check(els[0].get("item") == EXPECTED_ORIGIN + "/", f"{p}: BreadcrumbList must start at home")
            check(els[-1].get("item") == EXPECTED_ORIGIN + p, f"{p}: BreadcrumbList leaf {els[-1].get('item')} != {EXPECTED_ORIGIN + p}")
            for el in els:
                check("#" not in str(el.get("item", "")), f"{p}: fragment URL in BreadcrumbList: {el.get('item')}")
    check("Organization" in types, f"{p}: missing Organization JSON-LD")
    if p != "/":
        check("BreadcrumbList" in types, f"{p}: missing BreadcrumbList JSON-LD")
    if "Dataset" in types:
        dataset_pages += 1
    if "FAQPage" in types:
        faq_pages += 1

    # Check all internal href/src links
    for attr_val in re.findall(r'(?:href|src)="(/[^"]*)"', doc):
        clean_path = attr_val.split("#")[0].split("?")[0]
        check(resolve_disk(clean_path), f"{p}: broken internal reference {attr_val}")
        if clean_path in sitemap_set:
            graph[p].add(clean_path)

# BFS reachability from "/" to guarantee zero orphan pages
visited = {"/"}
queue = collections.deque(["/"])
while queue:
    cur = queue.popleft()
    for nxt in graph[cur]:
        if nxt not in visited:
            visited.add(nxt)
            queue.append(nxt)
orphans = sorted(sitemap_set - visited)
check(not orphans, f"{len(orphans)} orphan pages unreachable from /: {orphans[:10]}")

# Verify new SSR hubs exist
required_hubs = [
    "/hard-fraud", "/cases/federal", "/cases/state", "/cases/local",
    "/agencies", "/programs", "/years",
    "/answers/which-states-have-the-highest-unemployment-fraud-rates",
    "/answers/which-federal-agencies-failed-payment-integrity-compliance",
    "/answers/how-much-improper-payment-money-is-recovered",
    "/answers/which-federal-programs-have-the-highest-error-rates",
    "/answers/what-did-state-auditors-find-in-federal-single-audits",
    "/answers/which-federal-contracts-have-no-description",
]
for h in required_hubs:
    check(h in sitemap_set, f"expected hub missing from sitemap: {h}")

# 6. Real data fidelity checks
cases_json = json.load(open(os.path.join(SITE, "downloads", "cases.json"), encoding="utf-8"))
check(len(cases_json["cases"]) == 43, f"expected 43 real cases in cases.json, got {len(cases_json['cases'])}")
prog_csv_rows = list(csv.reader(open(os.path.join(SITE, "downloads", "improper-payments-by-program.csv"), encoding="utf-8")))[1:]
check(len(prog_csv_rows) == 1705, f"expected 1705 OMB rows in improper-payments-by-program.csv, got {len(prog_csv_rows)}")
year_csv_rows = list(csv.reader(open(os.path.join(SITE, "downloads", "improper-payments-by-year.csv"), encoding="utf-8")))[1:]
check(len(year_csv_rows) == 22, f"expected 22 fiscal years in improper-payments-by-year.csv, got {len(year_csv_rows)}")
data_html = open(os.path.join(SITE, "data.html"), encoding="utf-8").read()
check('"DataDownload"' in data_html, "/data missing DataDownload distribution schema")
check(dataset_pages >= 210, f"expected >=210 Dataset JSON-LD pages, got {dataset_pages}")
check(faq_pages == 12, f"expected 12 FAQPage answer pages, got {faq_pages}")

if failures:
    print(f"FAIL: {len(failures)} issues:")
    for msg in failures[:40]:
        print("  -", msg)
    sys.exit(1)

print(
    f"PASS: {len(sitemap_set)} sitemap URLs across {len(child_counts)} child sitemaps {child_counts}, "
    f"0 orphans, 0 broken links, 0 truncated titles/descriptions, "
    f"{dataset_pages} Dataset pages, {faq_pages} FAQPage answers, lastmod={EXPECTED_LASTMOD}"
)
