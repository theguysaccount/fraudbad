# Render 1200x630 social cards and icon PNGs with headless Chrome.
from browser import launch_args
import asyncio, html, os
from playwright.async_api import async_playwright
from content import CASES, TIERS, LEVELS
import content_soft  # noqa: F401  (adds soft-fraud cases and tiers)
import content_more as M  # round-3 cases + ledger totals

SITE = os.path.join(os.path.dirname(__file__), "site")
F = "file://" + SITE
e = lambda s: html.escape(str(s))

BASE = f"""<style>
@font-face{{font-family:Anton;src:url({F}/anton-latin.woff2)}}
@font-face{{font-family:PS;src:url({F}/publicsans-var-latin.woff2);font-weight:100 900}}
@font-face{{font-family:PM;src:url({F}/plexmono-600-latin.woff2);font-weight:600}}
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;overflow:hidden;background:#0a1f44;color:#fff;font-family:PS;position:relative}}
.mark{{position:absolute;left:64px;top:52px;font:400 40px/1 Anton;text-transform:uppercase;letter-spacing:.01em}}
.mark .f{{color:#ff4438}}
.lvl{{position:absolute;right:64px;top:60px;font:600 18px/1 PM;letter-spacing:.16em;text-transform:uppercase;color:#a9b4cc}}
.fig{{position:absolute;left:60px;top:120px;font:400 200px/.9 Anton;letter-spacing:.005em;white-space:nowrap}}
.scale{{position:absolute;left:66px;top:318px;font:400 50px/1 Anton;text-transform:uppercase;color:#ff4438;letter-spacing:.03em}}
.title{{position:absolute;left:66px;top:388px;width:1000px;font:800 44px/1.14 PS;letter-spacing:-.01em}}
.bar{{position:absolute;left:0;right:0;bottom:0;height:78px;background:#d71e28;display:flex;align-items:center;justify-content:space-between;padding:0 64px}}
.bar b{{font:400 30px/1 Anton;text-transform:uppercase;letter-spacing:.04em}}
.bar b span{{color:#0b0f1a}}
.bar i{{font:600 20px/1 PM;font-style:normal;letter-spacing:.08em}}
.tier{{display:inline-block;font:600 17px/1 PM;letter-spacing:.12em;text-transform:uppercase;padding:9px 12px;border:3px solid #fff;color:#fff;position:absolute;right:64px;top:96px}}
.rule{{position:absolute;left:64px;right:64px;top:104px;height:0}}
</style>"""


def case_card(c):
    fig = c["fig"]
    size = 200 if len(fig) <= 6 else (170 if len(fig) <= 8 else 150)
    return f"""<html><head>{BASE}</head><body>
<div class="mark"><span class="f">Fraud</span>Bad</div>
<div class="lvl">{e(LEVELS[c['level']])} · {e(c['place'])}</div>
<div class="tier" style="top:96px">{e(TIERS[c['tier']][0])}</div>
<div class="fig" style="font-size:{size}px;top:{120 + (200-size)//2}px">{e(fig)}</div>
<div class="scale">{e(c['scale'])}</div>
<div class="title">{e(c['title'])}</div>
<div class="bar"><b>Want to stop it? <span>Sign the Receipts Act.</span></b><i>fraudbad.com</i></div>
</body></html>"""


HOME = f"""<html><head>{BASE}</head><body>
<div class="mark"><span class="f">Fraud</span>Bad</div>
<div class="lvl">No taxation without receipts</div>
<div class="fig" style="font-size:176px;top:118px">$233–521</div>
<div class="scale" style="top:300px;font-size:62px">billion a year</div>
<div class="title" style="top:380px">Lost to fraud, by the government's own estimate. Every big case, sourced — and where the receipts stop.</div>
<div class="bar"><b>Want to stop it? <span>Sign the Receipts Act.</span></b><i>fraudbad.com</i></div>
</body></html>"""

TRANSP = f"""<html><head>{BASE}<style>
.grid{{position:absolute;right:64px;top:132px;display:grid;grid-template-columns:repeat(3,92px);gap:6px}}
.grid div{{height:46px;display:flex;align-items:center;justify-content:center;font:600 12px/1 PM;letter-spacing:.12em}}
.o{{background:#fff;color:#0a1f44}} .p{{background:#fff;color:#0b0f1a;background-image:repeating-linear-gradient(135deg,rgba(11,15,26,.18) 0 2px,transparent 2px 8px)}} .d{{background:#0b0f1a;color:#fff}} .r{{background:#d71e28;color:#fff}}
.h{{background:transparent!important;color:#a9b4cc!important;font-size:13px!important}}
</style></head><body>
<div class="mark"><span class="f">Fraud</span>Bad</div>
<div class="fig" style="font-size:82px;top:126px;line-height:.98;white-space:normal;width:640px">You can see the total. You can't see the receipt.</div>
<div class="title" style="top:430px;width:640px;font-size:32px">Where federal, state and city spending records stop.</div>
<div class="grid">
<div class="h">FEDERAL</div><div class="h">STATE</div><div class="h">LOCAL</div>
<div class="o">VISIBLE</div><div class="p">PARTLY</div><div class="p">PARTLY</div>
<div class="p">PARTLY</div><div class="p">PARTLY</div><div class="p">PARTLY</div>
<div class="p">PARTLY</div><div class="r">DARK</div><div class="o">VISIBLE</div>
<div class="r">DARK</div><div class="d">DARK</div><div class="r">DARK</div>
<div class="d">DARK</div><div class="d">DARK</div><div class="d">DARK</div>
<div class="d">DARK</div><div class="d">DARK</div><div class="d">DARK</div>
</div>
<div class="bar"><b>Want to stop it? <span>Sign the Receipts Act.</span></b><i>fraudbad.com/transparency</i></div>
</body></html>"""


LEDGER = f"""<html><head>{BASE}<style>
.yr{{position:absolute;right:64px;top:150px;width:470px;height:250px;display:flex;align-items:flex-end;gap:5px;border-bottom:3px solid #fff}}
.yr i{{flex:1;background:#fff;display:block}} .yr i.h{{background:#ff4438}}
</style></head><body>
<div class="mark"><span class="f">Fraud</span>Bad</div>
<div class="lvl">The ledger · every program</div>
<div class="fig" style="font-size:170px;top:132px">${M.CUM/1e12:.2f}T</div>
<div class="scale" style="top:312px;font-size:40px">paid wrong since {M.FIRST_YEAR}</div>
<div class="title" style="top:388px;width:560px;font-size:36px">Every federal program's error rate, from the government's own dataset.</div>
<div class="yr">{''.join(f'<i class="{"h" if y==max(M.YEARS) else ""}" style="height:{M.YEARS[y]["amount_m"]/max(v["amount_m"] for v in M.YEARS.values())*100:.0f}%"></i>' for y in sorted(M.YEARS))}</div>
<div class="bar"><b>Want to stop it? <span>Sign the Receipts Act.</span></b><i>fraudbad.com/ledger</i></div>
</body></html>"""

SOFT = f"""<html><head>{BASE}</head><body>
<div class="mark"><span class="f">Fraud</span>Bad</div>
<div class="lvl">Soft fraud</div>
<div class="tier" style="top:96px;border-color:#e9b949;color:#e9b949">Bigger than the crimes</div>
<div class="fig" style="font-size:190px;top:122px">${M.CUM/1e12:.2f}</div>
<div class="scale" style="top:318px;color:#e9b949">trillion paid wrong since {M.FIRST_YEAR}</div>
<div class="title">Soft fraud: paying without proof, overpaying, paying twice, never collecting. Here's how we search for it.</div>
<div class="bar"><b>Want to stop it? <span>Sign the Receipts Act.</span></b><i>fraudbad.com/soft-fraud</i></div>
</body></html>"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**launch_args())
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        jobs = [("og-home.png", HOME), ("og-transparency.png", TRANSP), ("og-soft-fraud.png", SOFT), ("og-ledger.png", LEDGER)] + [(f"og-{c['slug']}.png", case_card(c)) for c in CASES]
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa"), exist_ok=True)
        for name, doc in jobs:
            tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa", "_og.html")
            open(tmp, "w", encoding="utf-8").write(doc)
            await pg.goto("file://" + tmp)
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(120)
            over = await pg.evaluate("""() => [...document.querySelectorAll('.fig,.title,.scale')].filter(el => el.getBoundingClientRect().right > 1170 || el.getBoundingClientRect().bottom > 556).map(el => el.className)""")
            if over: print("OVERFLOW", name, over)
            await pg.screenshot(path=os.path.join(SITE, name), type="png")
        # icons from the SVG
        svg = open(os.path.join(SITE, "favicon.svg")).read()
        for size, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (512, "icon-512.png")):
            ip = await b.new_page(viewport={"width": size, "height": size})
            await ip.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg width=\'{size}\' height=\'{size}\' ")}</body></html>')
            await ip.screenshot(path=os.path.join(SITE, name), omit_background=(size == 32))
            await ip.close()
        await b.close()
    print("rendered", len(jobs), "cards + 3 icons")

asyncio.run(main())
