#!/usr/bin/env bash
# Build, check, and copy the site to the repo root. Commit and push are left to you (git add -A && git commit && git push).
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
python3 og.py
[ -d site/share-kit ] || python3 share_kit.py   # ~8 minutes; cards and clips persist in site/ between runs
# keep the share-kit page on the current stylesheet version (it isn't rebuilt every run)
V=$(sed -n 's/^V = "\([0-9a-z]*\)"/\1/p' build.py)
sed -i -E "s#/site\.css\?v=[0-9a-z]+#/site.css?v=$V#" site/share-kit/index.html
python3 check.py
python3 seo_audit.py
cd ..
find . -maxdepth 1 -type f ! -name README.md -delete
find . -mindepth 1 -maxdepth 1 -type d ! -name _build ! -name .git -exec rm -rf {} +
cp -a _build/site/. .
echo "site copied to repo root — review with git status, then commit and push"
