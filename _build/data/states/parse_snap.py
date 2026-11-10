"""Parse USDA's SNAP payment error rate PDFs into snap_per.json. Usage: python3 parse_snap.py"""
import json, re, subprocess
out = {}
for fy, f in ((2025, "snap_fy25.pdf"), (2024, "snap_fy24.pdf")):
    txt = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout
    for m in re.finditer(r"^\s+([A-Z][A-Z .]+?)\s{2,}([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$", txt, re.M):
        name = m.group(1).strip().title().replace(" Of ", " of ")
        out.setdefault(name, {})[fy] = {"over": float(m.group(2)), "under": float(m.group(3)), "rate": float(m.group(4))}
json.dump(out, open("snap_per.json", "w"), indent=1, sort_keys=True)
print(len(out), "rows;", out.get("United States"))
