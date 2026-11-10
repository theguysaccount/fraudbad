"""Check every built page against SEO-STANDARD.md (Jack's rules). Usage: python3 seo_audit.py  -> exit 1 on problems."""
import collections, html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
pages = []
for root, _, files in os.walk(SITE):
    for f in files:
        if f.endswith(".html"):
            rel = os.path.relpath(os.path.join(root, f), SITE)
            if rel.startswith(("embed/", "share-kit/")) or rel.startswith("google") or rel == "404.html":
                continue
            pages.append(rel)
probs, titles, descs = [], collections.defaultdict(list), collections.defaultdict(list)
for rel in sorted(pages):
    t = open(os.path.join(SITE, rel), encoding="utf-8").read()
    if re.search(r'<meta name="robots" content="[^"]*noindex', t):
        continue
    title = html.unescape((re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1].strip())
    desc = html.unescape((re.search(r'<meta name="description" content="([^"]*)"', t) or [None, ""])[1])
    h1 = len(re.findall(r"<h1\b", t))
    titles[title].append(rel); descs[desc].append(rel)
    if not title: probs.append((rel, "no <title>"))
    elif len(title) > 70: probs.append((rel, f"title {len(title)} chars (keep it under 70): {title}"))
    if not desc: probs.append((rel, "no meta description"))
    elif not 50 <= len(desc) <= 170: probs.append((rel, f"description {len(desc)} chars (aim 50-170)"))
    if h1 != 1: probs.append((rel, f"{h1} <h1> tags (want exactly 1)"))
    if 'rel="canonical"' not in t: probs.append((rel, "no canonical link"))
    if '"@type": "Organization"' not in t and '"@type":"Organization"' not in t: probs.append((rel, "no Organization schema"))
    for img in re.findall(r"<img\b[^>]*>", t):
        if " alt=" not in img: probs.append((rel, "image without alt text"))
    for a in re.findall(r'<a\b[^>]*href="https://america\.co[^>]*>', t):
        if "nofollow" not in a: probs.append((rel, "america.co link without rel=nofollow"))
for k, v in titles.items():
    if len(v) > 1: probs.append((v[0], f"title shared by {len(v)} pages: {k[:60]}"))
for k, v in descs.items():
    if len(v) > 1 and k: probs.append((v[0], f"description shared by {len(v)} pages"))
for rel, msg in probs:
    print(f"{rel}: {msg}")
print(f"seo audit: {len(pages)} pages, {len(probs)} problems")
sys.exit(1 if probs else 0)
