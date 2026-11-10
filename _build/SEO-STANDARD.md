# FraudBad page standard (plan item 3.1)

Built from Jack's own SEO rules: `safe-SEO-playbook.md` (Jun 14, 2026) and `PORTFOLIO_SEO_STRATEGY.md`, both in his Google Drive. Their core: **real links from real sites, and our own pages being genuinely good. Nothing automated, nothing that looks like a link network.**

## Every page (checked by `python3 seo_audit.py`, run in `deploy.sh`)

| Rule | How it's enforced |
|---|---|
| One clear `<title>`, unique, 70 characters or fewer, leading with the page's main search phrase | `fit_title()` in `build.py` picks the first candidate that fits, drops " \| FraudBad" before cutting anything; audit fails on duplicates or overlength |
| One meta description, unique, 50–170 characters | `fit_desc()` cuts at a sentence end; audit fails on duplicates or overlength |
| Exactly one `<h1>`, then logical `<h2>`s | audit |
| Canonical link and Organization schema on every page | `head()`; audit |
| Every image has alt text | audit |
| XML sitemap submitted in Google Search Console; IndexNow ping after each deploy | `sitemap.xml`, `GSC_FILE`, `INDEXNOW_KEY` |
| Passes mobile Core Web Vitals | Lighthouse mobile, Nov 10: home 98 performance; case page 99; accessibility, best practices and SEO all 100 |
| Internal links between related pages of this site (case ↔ program ↔ agency ↔ year ↔ state) | page templates |

## Links between Jack's own sites

Jack's rule: never interlink his own portfolio for ranking — that's the private-blog-network footprint Google devalues. FraudBad's only link out to his own properties is the call to sign on america.co. Every such link is marked `rel="nofollow"` (`own_brand_nofollow()` in `build.py`; the audit fails on any that isn't). No "our other sites" blocks, no footer link lists to other brands.

## Off-site (Phase 2, by hand only)

1. **Digital PR off our own data** — the best link source. One data story at a time, pitched to the reporters in the send queue doc. Never bulk.
2. **Reporter queries** — answer real requests on Connectively, Featured, Qwoted or SourceBottle (about 3 a week). Needs an account Jack creates.
3. **A small number of real listings, done once by hand** — e.g. a Product Hunt launch for the data, relevant data directories.
4. **Never:** automated account creation to place links, paste-site or forum-profile drops, buying links without `rel="sponsored"`, the same anchor text repeated across many sites.
