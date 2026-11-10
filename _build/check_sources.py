"""Confirm every cited source still loads. Writes source-check.md. Usage: python3 check_sources.py"""
import concurrent.futures as cf, subprocess, sys
import content, content_soft, content_more  # noqa: F401  (all three add sources)
from content import S

UA = "Mozilla/5.0 (FraudBad source check; +https://fraudbad.com/about)"


def probe(item):
    sid, (title, pub, date, url) = item
    out = subprocess.run(["curl", "-sS", "-L", "-o", "/dev/null", "-m", "25", "-A", UA, "-w", "%{http_code}", url], capture_output=True, text=True)
    code = out.stdout.strip() or "000"
    return sid, url, code, out.stderr.strip()[:120]


rows = []
with cf.ThreadPoolExecutor(8) as ex:
    for sid, url, code, err in ex.map(probe, sorted(S.items())):
        rows.append((sid, url, code, err))
ok = [r for r in rows if r[2].startswith(("2", "3"))]
dead = [r for r in rows if r[2] in ("404", "410")]
blocked = [r for r in rows if r not in ok and r not in dead]
with open("source-check.md", "w") as f:
    f.write(f"# Source check\n\n{len(rows)} sources: {len(ok)} load, {len(dead)} gone (404/410), {len(blocked)} refused or unreachable from the checker (check by hand).\n\n")
    for title, group in (("Gone", dead), ("Refused or unreachable", blocked)):
        f.write(f"## {title}\n\n" + ("".join(f"- `{s}` {c} {u} {e}\n" for s, u, c, e in group) or "None.\n") + "\n")
print(f"{len(rows)} sources: {len(ok)} load, {len(dead)} gone, {len(blocked)} refused/unreachable")
for s, u, c, e in dead + blocked:
    print(" ", c, s, u[:100], e[:60])
sys.exit(1 if dead else 0)
