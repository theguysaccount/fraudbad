#!/usr/bin/env bash
# Build, check, and copy the site to the repo root. Commit and push are left to you (git add -A && git commit && git push).
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
python3 og.py
python3 check.py
cd ..
find . -maxdepth 1 -type f ! -name README.md -delete
find . -mindepth 1 -maxdepth 1 -type d ! -name _build ! -name .git -exec rm -rf {} +
cp -a _build/site/. .
echo "site copied to repo root — review with git status, then commit and push"
