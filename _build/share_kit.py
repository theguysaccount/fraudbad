"""Share kit (plan item 1.8): for every case, a square card (1080x1080), a vertical card (1080x1920) and an
8-second clip of the receipt printing, plus captions.csv. Output: site/share-kit/ (served at fraudbad.com/share-kit).
Usage: python3 share_kit.py [--no-clips]"""
import asyncio, csv, html, os, shutil, subprocess, sys
from playwright.async_api import async_playwright
from browser import launch_args
import build as B  # noqa: E402  (loads every case)
import threading
from serve import serve

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(B.OUT, "share-kit")
F = "file://" + os.path.join(HERE, "assets")
e = html.escape

CSS = f"""<style>
@font-face{{font-family:Anton;src:url({F}/anton-latin.woff2)}}
@font-face{{font-family:PS;src:url({F}/publicsans-var-latin.woff2);font-weight:100 900}}
@font-face{{font-family:PM;src:url({F}/plexmono-600-latin.woff2);font-weight:600}}
*{{box-sizing:border-box;margin:0}}
body{{width:1080px;overflow:hidden;background:#0a1f44;color:#fff;font-family:PS;display:flex;flex-direction:column;padding:72px 72px 0}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.mark{{font:400 46px/1 Anton;text-transform:uppercase}} .mark .f{{color:#ff4438}}
.tier{{font:600 20px/1 PM;letter-spacing:.12em;text-transform:uppercase;padding:10px 14px;border:3px solid #fff}}
.lvl{{font:600 20px/1.3 PM;letter-spacing:.14em;text-transform:uppercase;color:#a9b4cc;margin-top:40px}}
.fig{{font:400 var(--fs)/.92 Anton;margin-top:18px;white-space:nowrap}}
.scale{{font:400 58px/1 Anton;text-transform:uppercase;color:#ff4438;margin-top:12px}}
.title{{font:800 54px/1.12 PS;letter-spacing:-.01em;margin-top:30px}}
.dek{{font:400 34px/1.35 PS;color:#dfe5f2;margin-top:28px}}
.src{{font:600 22px/1.4 PM;color:#a9b4cc;margin-top:28px}}
.bar{{margin:auto -72px 0;background:#d71e28;padding:30px 72px;display:flex;justify-content:space-between;align-items:center}}
.bar b{{font:400 40px/1.05 Anton;text-transform:uppercase}} .bar b span{{color:#0b0f1a;display:block}}
.bar i{{font:600 24px/1 PM;font-style:normal}}
</style>"""


def card(c, h):
    fig = c["fig"]
    fs = 250 if len(fig) <= 6 else (200 if len(fig) <= 8 else 170)
    src = B.S[c["sources"][0]][1].split(";")[0].split(",")[0]
    dek = f'<div class="dek">{e(c["dek"])}</div>' if h > 1200 else ""
    return f"""<html><head>{CSS}</head><body style="height:{h}px;--fs:{fs}px">
<div class="top"><div class="mark"><span class="f">Fraud</span>Bad</div><div class="tier">{e(B.TIERS[c['tier']][0])}</div></div>
<div class="lvl">{e(B.LEVELS[c['level']])} · {e(c['place'])}</div>
<div class="fig">{e(fig)}</div><div class="scale">{e(c['scale'])}</div>
<div class="title">{e(c['title'])}</div>{dek}
<div class="src">Source: {e(src)}</div>
<div class="bar"><b>Want to stop it?<span>Sign the Receipts Act.</span></b><i>fraudbad.com/{e(c['slug'])}</i></div>
</body></html>"""


async def main(clips):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(HERE, "qa", "_share.html")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_args())
        for size, h in (("square", 1080), ("vertical", 1920)):
            pg = await b.new_page(viewport={"width": 1080, "height": h})
            for c in B.ORDERED:
                open(tmp, "w", encoding="utf-8").write(card(c, h))
                await pg.goto("file://" + tmp)
                await pg.evaluate("document.fonts.ready")
                over = await pg.evaluate("() => document.body.scrollHeight > innerHeight + 2 || [...document.querySelectorAll('.fig')].some(x => x.getBoundingClientRect().right > 1060)")
                if over:
                    print("OVERFLOW", size, c["slug"])
                await pg.screenshot(path=os.path.join(OUT, f"{c['slug']}-{size}.png"))
            await pg.close()
        if clips:
            httpd = serve(8798)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            vdir = os.path.join(HERE, "qa", "_video")
            for c in B.ORDERED:
                shutil.rmtree(vdir, ignore_errors=True)
                ctx = await b.new_context(viewport={"width": 1080, "height": 1920}, device_scale_factor=1, record_video_dir=vdir, record_video_size={"width": 1080, "height": 1920})
                pg = await ctx.new_page()
                await pg.goto(f"http://127.0.0.1:8798/embed/{c['slug']}")
                await pg.add_style_tag(content="html,body.embed{height:1920px}body.embed{background:#0a1f44!important;display:flex;align-items:center;justify-content:center}.embed-wrap{max-width:330px;zoom:3}.embed-credit{font-size:11px}.embed-credit a{color:#fff!important}")
                await pg.wait_for_timeout(8000)
                await ctx.close()
                webm = [f for f in os.listdir(vdir) if f.endswith(".webm")][0]
                mp4 = os.path.join(OUT, f"{c['slug']}-clip.mp4")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(vdir, webm), "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", mp4], check=True)
            shutil.rmtree(vdir, ignore_errors=True)
            httpd.shutdown()
        await b.close()
    with open(os.path.join(OUT, "captions.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["slug", "caption", "link"])
        for c in B.ORDERED:
            link = f"{B.SITE}/{c['slug']}"
            w.writerow([c["slug"], f"{c['fig']} {c['scale']}. {c['title'].rstrip('.')}. Every number, sourced:", link])
    print("share kit:", len(os.listdir(OUT)), "files")





def index_page():
    """Plain list of every file in the kit with its caption (noindex; for whoever runs the socials)."""
    rows = []
    caps = {r["slug"]: r for r in csv.DictReader(open(os.path.join(OUT, "captions.csv"), encoding="utf-8"))}
    for c in B.ORDERED:
        s = c["slug"]
        rows.append(f"""<tr><td><b>{e(c['title'])}</b><span class="ag">{e(caps[s]['caption'])} {e(caps[s]['link'])}</span></td>
<td><a href="/share-kit/{s}-square.png" download>Square</a> · <a href="/share-kit/{s}-vertical.png" download>Vertical</a> · <a href="/share-kit/{s}-clip.mp4" download>Clip</a></td></tr>""")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Share kit | FraudBad</title><meta name="robots" content="noindex"><link rel="stylesheet" href="/site.css?v={B.V}"></head>
<body><main class="sec"><div class="wrap"><p class="kicker" style="color:var(--red)">For whoever posts</p><h1 style="font-size:64px">Share kit</h1>
<p class="lede" style="margin:12px 0 28px">Every case as a square card, a vertical card and an 8-second clip, with a caption. <a href="/share-kit/captions.csv" download>All captions (CSV)</a> · <a href="/share-kit/calendar.csv" download>Six-week posting calendar (CSV)</a>.</p>
<div class="tbl-wrap"><table class="tbl fit"><thead><tr><th>Case and caption</th><th>Files</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div></main></body></html>"""
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)





def calendar():
    """Plan item 2.7: 43 posts, one a day, alternating hard and soft fraud, biggest first. Sign links tagged by platform."""
    hard = sorted([c for c in B.ORDERED if c["type"] == "hard"], key=lambda c: -c["sort"])
    soft = sorted([c for c in B.ORDERED if c["type"] == "soft"], key=lambda c: -c["sort"])
    order = []
    while hard or soft:
        if soft: order.append(soft.pop(0))
        if hard: order.append(hard.pop(0))
    with open(os.path.join(OUT, "calendar.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["day", "week", "case", "caption", "x_and_youtube_link", "instagram", "square", "vertical", "clip"])
        for i, c in enumerate(order, 1):
            s_ = c["slug"]
            sign = lambda ref: f"https://america.co/receipts-act?ref={ref}&case={s_}#sign"
            w.writerow([i, (i - 1) // 7 + 1, s_, f"{c['fig']} {c['scale']}. {c['title'].rstrip('.')}. Every number, sourced: fraudbad.com/{s_} — Want to stop it? Sign the RECEIPTS Act.",
                        sign("x"), "Sign link in bio: " + sign("ig"), f"{B.SITE}/share-kit/{s_}-square.png", f"{B.SITE}/share-kit/{s_}-vertical.png", f"{B.SITE}/share-kit/{s_}-clip.mp4"])
    return len(order)


if __name__ == "__main__":
    if "--calendar" in sys.argv:
        print(calendar(), "posts")
        index_page()
    elif "--index-only" in sys.argv:
        index_page()
    else:
        asyncio.run(main("--no-clips" not in sys.argv))
        calendar()
        index_page()
