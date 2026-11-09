# fraudbad.com

Every major case of public-spending fraud in federal, state and local government — sourced to the auditors, inspectors general, prosecutors and courts that found it — plus a map of where public spending records stop.

- Live site: https://fraudbad.com
- Every figure lives in `_build/content.py` with its source. Nothing ships without one.
- Rebuild: `cd _build && python3 build.py && python3 og.py` (outputs to `_build/site/`; copy to the repo root).
- Hosting: GitHub Pages from `main` (root). `CNAME` sets the custom domain.

Corrections: send the source via https://america.co/work-with-us
