"""Find 119th-Congress bills on improper payments, payment integrity and spending transparency.
Input: govinfo BILLSTATUS bulk XML (unzipped dirs given as args). Output: bills_payment_integrity.json beside this file.
Usage: python3 -I parse_bills.py <dir_with_hr_xml> <dir_with_s_xml>"""
import json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"improper payment|payment integrity|do not pay|program integrity|fraud prevention|prevent(ing)? fraud|"
                 r"fraud(ulent)? (and|or) (waste|improper)|waste,? fraud|deceased|death master|death data|recovery audit|"
                 r"spending transparency|usaspending|data act|subaward|federal spending|taxpayer dollars|"
                 r"identity verification|unemployment (insurance )?fraud|snap fraud|medicaid fraud|medicare fraud|"
                 r"fraud risk|antifraud|anti-fraud|grant reform|grants? transparency|financial management|audit", re.I)


def txt(el, path):
    x = el.find(path)
    return x.text.strip() if x is not None and x.text else ""


def bills(d):
    for f in os.listdir(d):
        if not f.endswith(".xml"):
            continue
        b = ET.parse(os.path.join(d, f)).getroot().find("bill")
        titles = [t.findtext("title") or "" for t in b.findall("titles/item")]
        title = txt(b, "title")
        hit = [t for t in [title] + titles if PAT.search(t)]
        if not hit:
            continue
        sp = b.find("sponsors/item")
        cos = b.findall("cosponsors/item")
        yield {
            "bill": f"{txt(b, 'type')} {txt(b, 'number')}".upper(),
            "type": txt(b, "type").lower(), "number": txt(b, "number"),
            "title": title, "matched": hit[0],
            "introduced": txt(b, "introducedDate"),
            "sponsor": {k: txt(sp, k) for k in ("bioguideId", "fullName", "party", "state", "district")} if sp is not None else {},
            "cosponsors": [{k: txt(c, k) for k in ("bioguideId", "fullName", "party", "state")} for c in cos],
            "latest_action": txt(b, "latestAction/text"), "latest_date": txt(b, "latestAction/actionDate"),
            "policy_area": txt(b, "policyArea/name"),
            "committees": sorted({txt(c, "name") for c in b.findall("committees/item")} - {""}),
            "laws": [txt(l, "number") for l in b.findall("laws/item")],
        }


if __name__ == "__main__":
    out = [x for d in sys.argv[1:] for x in bills(d)]
    out.sort(key=lambda x: (x["type"], int(x["number"])))
    json.dump(out, open(os.path.join(HERE, "bills_payment_integrity.json"), "w"), indent=1)
    print(len(out), "bills matched")
