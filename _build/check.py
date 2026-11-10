"""Site check: every page in the sitemap at phone and desktop width.

Fails (exit 1) on: sideways scroll, a script error, a broken internal link, a Sign link without its tags,
a page missing from the sitemap, or a page without a title, description or social image.
Usage: python3 check.py [--shots DIR] [--widths 390,1440]
"""
import argparse, asyncio, html.parser, os, re, sys, threading
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from browser import launch_args
from serve import serve, ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--shots", default="")
ap.add_argument("--widths", default="390,1440")
ap.add_argument("--only", default="", help="comma list of paths to check instead of the whole sitemap")
args = ap.parse_args()
WIDTHS = [int(w) for w in args.widths.split(",")]
PORT = 8799
fails = []


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs = []; self.meta = {}; self.title = ""; self._t = False
    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "a" and a.get("href"): self.hrefs.append(a["href"])
        if tag in ("img", "script") and a.get("src"): self.hrefs.append(a["src"])
        if tag == "link" and a.get("href") and a.get("rel") in ("stylesheet", "icon", "manifest", "apple-touch-icon"): self.hrefs.append(a["href"])
        if tag == "meta" and (a.get("name") or a.get("property")): self.meta[a.get("name") or a.get("property")] = a.get("content", "")
        if tag == "title": self._t = True
    def handle_endtag(self, tag):
        if tag == "title": self._t = False
    def handle_data(self, d):
        if self._t: self.title += d


def exists(path):
    path = path.split("#")[0].split("?")[0]
    if path in ("", "/"): return os.path.exists(os.path.join(ROOT, "index.html"))
    p = os.path.join(ROOT, path.lstrip("/"))
    return os.path.isfile(p) or os.path.isfile(p + ".html") or os.path.isfile(os.path.join(p, "index.html"))


sitemap = open(os.path.join(ROOT, "sitemap.xml")).read()
paths = [urlparse(u).path or "/" for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]
on_disk = set()
for dp, _, fs in os.walk(ROOT):
    for f in fs:
        if f.endswith(".html") and f != "404.html" and not f.startswith("google"):
            rel = os.path.relpath(os.path.join(dp, f), ROOT)[:-5]
            on_disk.add("/" if rel == "index" else "/" + rel)
for p in sorted(on_disk - set(paths)):
    if not p.startswith(("/embed/", "/share-kit")):
        fails.append(f"not in sitemap: {p}")

# static checks on every page
for p in sorted(on_disk):
    f = os.path.join(ROOT, "index.html" if p == "/" else p.lstrip("/") + ".html")
    L = Links(); L.feed(open(f, encoding="utf-8").read())
    if not L.title.strip(): fails.append(f"{p}: no <title>")
    if not p.startswith(("/embed/", "/share-kit")):
        for k in ("description", "og:image"):
            if not L.meta.get(k): fails.append(f"{p}: no {k}")
    for h in L.hrefs:
        u = urlparse(h)
        if u.scheme in ("http", "https"):
            if "america.co/receipts-act" in h and "#sign" in h and ("ref=fraudbad" not in h or "case=" not in h):
                fails.append(f"{p}: untagged Sign link {h}")
            continue
        if u.scheme or h.startswith("#") or h.startswith("mailto:"): continue
        if not exists(u.path): fails.append(f"{p}: broken link {h}")

if args.only:
    paths = args.only.split(",")


async def browse():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(**launch_args())
        for w in WIDTHS:
            ctx = await b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1, reduced_motion="reduce")
            pg = await ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            for p in paths:
                errs.clear()
                r = await pg.goto(f"http://127.0.0.1:{PORT}{p}", wait_until="load")
                if not r or r.status != 200: fails.append(f"{p} @{w}: HTTP {r.status if r else 'none'}")
                await pg.wait_for_timeout(150)
                sw = await pg.evaluate("document.documentElement.scrollWidth")
                if sw > w: fails.append(f"{p} @{w}: sideways scroll ({sw}px)")
                for e in errs: fails.append(f"{p} @{w}: script error: {e[:160]}")
                if args.shots:
                    os.makedirs(args.shots, exist_ok=True)
                    name = (p.strip("/") or "home").replace("/", "_")
                    await pg.screenshot(path=os.path.join(args.shots, f"{name}-{w}.png"), full_page=True)
            await ctx.close()
        await b.close()


httpd = serve(PORT)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
asyncio.run(browse())
httpd.shutdown()
print(f"checked {len(paths)} pages at {WIDTHS}: {len(fails)} problems")
for f in fails[:80]:
    print("  -", f)
sys.exit(1 if fails else 0)
