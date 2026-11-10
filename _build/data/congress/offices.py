"""Plan item 2.4: 25 member offices, each with that member's own record on payment integrity and spending transparency
(119th Congress, read from govinfo BILLSTATUS XML) and their public contact route (unitedstates/congress-legislators).
Usage: python3 -I offices.py <bulk_xml_root containing hr/ and s/>  ->  offices_wave3.csv + offices_wave3.md"""
import csv, os, sys, datetime as dt
import xml.etree.ElementTree as ET
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

# bioguide -> [(bill, role)]  role: S = sponsor, C = cosponsor.  Chosen because the bill is about improper payments,
# fraud in federal programs, or public spending records; committee leaders included for jurisdiction.
PICKS = [
    ("E000295", [("s3902", "S"), ("s4130", "S"), ("s872", "S")]),            # Ernst
    ("K000393", [("s269", "S")]),                                            # Kennedy
    ("R000618", [("s747", "S")]),                                            # Ricketts
    ("L000575", [("s75", "S"), ("s4016", "S"), ("s872", "C")]),               # Lankford
    ("C001098", [("s3862", "S")]),                                           # Cruz
    ("P000603", [("s5185", "C")]),                                           # Paul (HSGAC chair)
    ("P000595", [("s872", "C"), ("s269", "C")]),                              # Peters (HSGAC ranking)
    ("H001076", [("s75", "C"), ("s269", "C"), ("s872", "C")]),                # Hassan
    ("K000394", [("s5167", "S")]),                                           # Andy Kim
    ("C001113", [("s5326", "S")]),                                           # Cortez Masto
    ("C001108", [("hr8463", "S"), ("hr5578", "C")]),                          # Comer (Oversight chair)
    ("G000598", [("hr5578", "S"), ("hr8463", "C")]),                          # Robert Garcia (Oversight ranking)
    ("M001241", [("hr8340", "S")]),                                          # Dave Min
    ("K000389", [("hr8107", "S")]),                                          # Khanna
    ("S001224", [("hr6916", "S")]),                                          # Self
    ("S000250", [("hr8312", "S")]),                                          # Sessions
    ("G000576", [("hr8428", "S")]),                                          # Grothman
    ("P000609", [("hr8467", "S")]),                                          # Palmer
    ("F000459", [("hr428", "S")]),                                           # Fleischmann
    ("Y000067", [("hr1771", "S")]),                                          # Yakym
    ("M001204", [("hr1533", "S")]),                                          # Meuser
    ("M001212", [("hr2069", "S")]),                                          # Barry Moore
    ("L000600", [("hr519", "S")]),                                           # Langworthy
    ("C001119", [("hr7155", "S")]),                                          # Craig
    ("P000607", [("hr7555", "S")]),                                          # Pocan
]


def d(s):
    return dt.date.fromisoformat(s).strftime("%b %-d, %Y")


def bill_info(root, key):
    t = "hr" if key.startswith("hr") else "s"
    b = ET.parse(os.path.join(root, t, f"BILLSTATUS-119{key}.xml")).getroot().find("bill")
    short = b.findtext("title")
    label = ("H.R. " if t == "hr" else "S. ") + key[len(t):]
    acts = [(a.findtext("actionDate"), a.findtext("text") or "") for a in b.findall("actions/item")]
    law = [x for x in acts if x[1].startswith("Became Public Law")]
    if law:
        status = f"law (Public Law {law[0][1].split('No: ')[-1].rstrip('.')}, {d(law[0][0])})"
    else:
        p = sorted(x[0] for x in acts if "Passed/agreed to in" in x[1] or x[1].startswith("On passage Passed"))
        ch = "House" if t == "hr" else "Senate"
        status = f"passed the {ch} {d(p[0])}" if p else f"introduced {d(b.findtext('introducedDate'))}"
    return label, short, status, f"https://www.congress.gov/bill/119th-congress/{'house' if t == 'hr' else 'senate'}-bill/{key[len(t):]}"


def main(root):
    L = {l["id"]["bioguide"]: l for l in yaml.safe_load(open(os.path.join(RAW, "legislators-current.yaml")))}
    M = yaml.safe_load(open(os.path.join(RAW, "committee-membership-current.yaml")))
    roles = {}
    for cid, cname in (("HSGO", "House Oversight"), ("SSGA", "Senate Homeland Security & Governmental Affairs")):
        for m in M[cid]:
            roles[m["bioguide"]] = cname + (f" ({m['title'].replace('Chairman', 'Chair')})" if m.get("title") else "")
    rows = []
    for bg, bills in PICKS:
        p = L[bg]
        t = p["terms"][-1]
        ch = "Sen." if t["type"] == "sen" else "Rep."
        where = t["state"] if t["type"] == "sen" else f"{t['state']}-{t['district'] if t['district'] else 'AL'}"
        rec = []
        for key, role in bills:
            label, short, status, url = bill_info(root, key)
            rec.append((("Sponsor" if role == "S" else "Cosponsor") + f" of {label} {short}: {status}", url))
        rows.append({
            "member": f"{ch} {p['name'].get('official_full') or p['name']['first'] + ' ' + p['name']['last']}",
            "party_state": f"{t['party'][0]}-{where}", "committee": roles.get(bg, ""),
            "record": " · ".join(r for r, _ in rec), "record_links": " ".join(u for _, u in rec),
            "contact": t.get("contact_form") or t.get("url", ""), "contact_kind": "Contact form" if t.get("contact_form") else "Website", "phone": t.get("phone", ""),
            "term_ends": d(t["end"]), "bioguide": bg,
        })
    with open(os.path.join(HERE, "offices_wave3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = ["| Office | Committee | Their record (119th Congress) | Contact | Term ends |", "|---|---|---|---|---|"]
    for r in rows:
        links = r["record_links"].split()
        parts = r["record"].split(" · ")
        rec = "; ".join(f"[{x.split(':')[0]}]({u}):{x.split(':', 1)[1]}" for x, u in zip(parts, links))
        md.append(f"| {r['member']} ({r['party_state']}) | {r['committee'] or '—'} | {rec} | [{r['contact_kind']}]({r['contact']}) · {r['phone']} | {r['term_ends']} |")
    open(os.path.join(HERE, "offices_wave3.md"), "w").write("\n".join(md) + "\n")
    print(len(rows), "offices")


if __name__ == "__main__":
    main(sys.argv[1])
