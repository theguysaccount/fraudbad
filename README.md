# fraudbad.com

Every major case of public-spending fraud and waste in federal, state and local government — sourced to the auditors, inspectors general, prosecutors and courts that found it — plus the government's own improper-payment ledger, page by page, and a map of where public spending records stop.

- Live site: https://fraudbad.com · Plan: "FraudBad: the rest of the plan" (Claude Docs)
- Every figure lives in `_build/content*.py` or `_build/data/` with its source. Nothing ships without one.

## Build, check, deploy

```
cd _build
python3 build.py        # writes _build/site/
python3 og.py           # social cards + icons
python3 check.py        # every sitemap page at 390 and 1440 px: sideways scroll, script errors, broken links, untagged Sign links
./deploy.sh             # build + cards + check, then copies site/ to the repo root; then git add -A, commit, push main
python3 check_sources.py  # confirms every cited source still loads
python3 share_kit.py      # square + vertical cards and 8-second clips per case -> /share-kit (about 8 minutes)
```

Needs Python 3 with `openpyxl` and `playwright` (Chromium), plus `ffmpeg` for clips.

## How the pieces fit

- `content.py`, `content_soft.py`, `content_more.py`: the cases and every source.
- `pages_more.py`: program, agency, year and state pages, /data, /about, /corrections, /contracts, /your-share, embeds, feed.
- Every link to the signing page carries `ref=fraudbad`, the page slug and the button position; the build fails if one doesn't. See `HANDOFF-america-co.md` for the america.co side.
- Hosting: GitHub Pages from `main` (root). `CNAME` sets fraudbad.com.

Corrections: https://fraudbad.com/corrections · send a source via https://america.co/work-with-us
