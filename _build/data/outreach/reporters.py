"""Plan item 2.5: statehouse/watchdog reporters per state, read Nov 10, 2026 from each outlet's own staff page
(titles exactly as the page shows them). Builds reporters_wave4.csv + .md with each state's hook from FraudBad's data.
Usage: python3 -I reporters.py"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.dirname(os.path.dirname(HERE))
R = {  # code: (outlet, staff page, [(name, title), ...])
 "AL": ("Alabama Reflector", "https://alabamareflector.com/about", [("Brian Lyman", "Editor"), ("Ralph Chapoco", "Senior Reporter")]),
 "AK": ("Alaska Beacon", "https://alaskabeacon.com/about", [("Claire Stremple", "Editor-in-Chief"), ("James Brooks", "Reporter")]),
 "AZ": ("Arizona Mirror", "https://azmirror.com/about", [("Caitlin Sievers", "Deputy Editor"), ("Jerod Macdonald-Evoy", "Reporter")]),
 "AR": ("Arkansas Advocate", "https://arkansasadvocate.com/about", [("Andrew DeMillo", "Editor-in-Chief"), ("Tess Vrbin", "Reporter")]),
 "CA": ("CalMatters", "https://calmatters.org/about/team/", [("Kristen Go", "Editor in Chief"), ("Jeanne Kuang", "Capitol Reporter")]),
 "CO": ("Colorado Newsline", "https://coloradonewsline.com/about", [("Quentin Young", "Editor"), ("Chase Woodruff", "Senior Reporter")]),
 "CT": ("CT Mirror", "https://ctmirror.org/about/", [("Keith Phaneuf", "State budget reporter")]),
 "FL": ("Florida Phoenix", "https://floridaphoenix.com/about", [("Michael Moline", "Editor-in-Chief"), ("Christine Sexton", "Senior Reporter")]),
 "GA": ("Georgia Recorder", "https://georgiarecorder.com/about", [("Jill Nolin", "Editor-in-Chief"), ("Ross Williams", "Deputy Editor")]),
 "HI": ("Honolulu Civil Beat", "https://www.civilbeat.org/2026/11/blue-tsunami-missed-hawaiis-capitol-but-dems-nabbed-3-seats/", [("Chad Blair", "Wrote Civil Beat's Nov 2026 Capitol election story (title not checked)")]),
 "ID": ("Idaho Capital Sun", "https://idahocapitalsun.com/about", [("Christina Lords", "Editor-in-Chief"), ("Clark Corbin", "Senior Reporter")]),
 "IN": ("Indiana Capital Chronicle", "https://indianacapitalchronicle.com/about", [("Niki Kelly", "Editor-in-Chief"), ("Casey Smith", "Senior Reporter")]),
 "IA": ("Iowa Capital Dispatch", "https://iowacapitaldispatch.com/about/", [("Kathie Obradovich", "Editor-in-Chief"), ("Clark Kauffman", "Deputy Editor")]),
 "KS": ("Kansas Reflector", "https://kansasreflector.com/about/", [("Sherman Smith", "Editor in chief"), ("Tim Carpenter", "Senior reporter")]),
 "KY": ("Kentucky Lantern", "https://kentuckylantern.com/about/", [("Linda Blackford", "Editor"), ("Sarah Ladd", "Reporter")]),
 "LA": ("Louisiana Illuminator", "https://lailluminator.com/about/", [("Greg LaRose", "Editor"), ("Julie O'Donoghue", "Senior Reporter")]),
 "ME": ("Maine Morning Star", "https://mainemorningstar.com/about/", [("Lauren McCauley", "Editor and reporter"), ("Emma Davis", "Reporter")]),
 "MD": ("Maryland Matters", "https://marylandmatters.org/about/", [("Steve Crane", "Editor-in-chief"), ("Bryan Sears", "Reporter")]),
 "MI": ("Michigan Advance", "https://michiganadvance.com/about/", [("Jon King", "Editor-in-Chief"), ("Ben Solis", "Senior Reporter")]),
 "MN": ("Minnesota Reformer", "https://minnesotareformer.com/about", [("J. Patrick Coolican", "Editor-in-Chief"), ("Michelle Griffith", "Reporter")]),
 "MS": ("Mississippi Today", "https://mississippitoday.org/2025/09/29/emily-wagster-pettus-editor-chief/", [("Emily Wagster Pettus", "Editor-in-Chief (named Sep 29, 2025)")]),
 "MO": ("Missouri Independent", "https://missouriindependent.com/about/", [("Jason Hancock", "Editor-in-Chief"), ("Rudi Keller", "Deputy Editor")]),
 "MT": ("Daily Montanan", "https://dailymontanan.com/about/", [("Darrell Ehrlick", "Editor-in-chief"), ("Keila Szpaller", "Deputy Editor")]),
 "NE": ("Nebraska Examiner", "https://nebraskaexaminer.com/about/", [("Joan von Kampen", "Editor in Chief"), ("Cindy Gonzalez", "Senior Reporter")]),
 "NV": ("Nevada Current", "https://nevadacurrent.com/about/", [("Hugh Jackson", "Editor"), ("Dana Gentry", "Senior Reporter")]),
 "NH": ("New Hampshire Bulletin", "https://newhampshirebulletin.com/about/", [("Dana Wormald", "Editor-in-Chief"), ("Ethan DeWitt", "Reporter")]),
 "NM": ("Source New Mexico", "https://sourcenm.com/about/", [("Julia Goldberg", "Editor-in-Chief"), ("Joshua Bowling", "Senior Reporter")]),
 "NC": ("NC Newsline", "https://ncnewsline.com/about/", [("Rob Schofield", "Editor"), ("Joe Killian", "Senior Investigative Reporter")]),
 "OH": ("Ohio Capital Journal", "https://ohiocapitaljournal.com/about/", [("David DeWitt", "Editor in Chief"), ("Marty Schladen", "Senior Reporter")]),
 "OK": ("Oklahoma Voice", "https://oklahomavoice.com/about/", [("Janelle Stecklein", "Editor"), ("Carmen Forman", "Reporter")]),
 "OR": ("Oregon Capital Chronicle", "https://oregoncapitalchronicle.com/about/", [("Julia Shumway", "Editor"), ("Alex Baumhardt", "Senior reporter")]),
 "PA": ("Pennsylvania Capital-Star", "https://penncapital-star.com/about/", [("Tim Lambert", "Editor-in-chief"), ("Peter Hall", "Senior Reporter")]),
 "RI": ("Rhode Island Current", "https://rhodeislandcurrent.com/about/", [("Janine L. Weisman", "Editor-in-Chief"), ("Nancy Lavin", "Senior Reporter")]),
 "SC": ("SC Daily Gazette", "https://scdailygazette.com/about/", [("Seanna Adcox", "Editor"), ("Jessica Holdman", "Senior Reporter")]),
 "SD": ("South Dakota Searchlight", "https://southdakotasearchlight.com/about/", [("Seth Tupper", "Editor-in-Chief"), ("John Hult", "Senior Reporter")]),
 "TN": ("Tennessee Lookout", "https://tennesseelookout.com/about/", [("Holly McCall", "Editor"), ("Anita Wadhwani", "Senior Reporter")]),
 "TX": ("The Texas Tribune", "https://www.texastribune.org/2025/07/02/texas-tribune-politics-investigations/", [("Jasper Scherer", "Politics editor (Jul 2025)"), ("Eleanor Klibanoff", "Politics reporter (Jul 2025)")]),
 "VT": ("VTDigger", "https://vtdigger.org/our-team/", [("Sue Allen", "Interim Editor-in-Chief"), ("Shaun Robinson", "State Government & Politics Reporter")]),
 "WA": ("Washington State Standard", "https://washingtonstatestandard.com/about/", [("Sean Robinson", "Editor (named Oct 28, 2026 in the Standard's own announcement; the About page still lists the previous editor)"), ("Jerry Cornfield", "Reporter")]),
 "WV": ("West Virginia Watch", "https://westvirginiawatch.com/about/", [("Leann Ray", "Editor"), ("Lori Kersey", "Deputy Editor")]),
 "WI": ("Wisconsin Examiner", "https://wisconsinexaminer.com/about/", [("Ruth Conniff", "Editor-in-Chief"), ("Erik Gunn", "Deputy Editor")]),
 "WY": ("WyoFile", "https://wyofile.com/about/staff/", [("Joshua Wolfson", "Editor-in-chief"), ("Maggie Mullen", "State government and politics reporter")]),
}
OPEN = {  # outlet whose staff page refused automated reading: open it in a browser to fill the names
 "IL": ("Capitol News Illinois", "https://capitolnewsillinois.com/about-us/", "general desk: editors@capitolnewsillinois.com"),
 "ND": ("North Dakota Monitor", "https://northdakotamonitor.com/about/", ""),
 "UT": ("Utah News Dispatch", "https://utahnewsdispatch.com/about/", ""),
 "NJ": ("New Jersey Monitor", "https://newjerseymonitor.com/about/", ""),
 "VA": ("Virginia Mercury", "https://virginiamercury.com/about/", ""),
 "DE": ("Spotlight Delaware", "https://spotlightdelaware.org/", "not checked"),
 "DC": ("The 51st", "https://51st.news/", "not checked"),
 "MA": ("CommonWealth Beacon", "https://commonwealthbeacon.org/", "not checked"),
 "NY": ("New York Focus", "https://nysfocus.com/", "not checked"),
}
if __name__ == "__main__":
    sys.path.insert(0, B)
    import pages_more as P
    from state_audits import A
    rows, _ = P.states_data()
    ui = P.ui_data()
    codes = {r["code"] for r in rows}
    ui_rank = {c: i for i, c in enumerate(sorted((c for c in ui if c in codes and "2026-03-31" in ui[c]), key=lambda c: -ui[c]["2026-03-31"]["ipr"]), 1)}
    by = {r["code"]: r for r in rows}
    out = []
    for code in sorted(by, key=lambda c: by[c]["name"]):
        r = by[code]
        u = ui.get(code, {}).get("2026-03-31")
        hook = f"{r['name']} is #{r['rank']} of 51 for food-benefit (SNAP) payment errors ({r['rate25']:.2f}%)"
        if u: hook += f" and #{ui_rank[code]} for jobless benefits paid wrong ({u['ipr']:.2f}%)"
        a = A.get(code)
        if a and a["basis"] != "none":
            hook += f"; its auditors flagged {a['figure']} ({a['program']})"
        page = f"https://fraudbad.com/state/{code.lower()}"
        if code in R:
            outlet, src, people = R[code]
            for n, t in people:
                out.append({"state": r["name"], "outlet": outlet, "name": n, "title": t, "read_from": src, "page": page, "hook": hook + "."})
        if code in OPEN or (code in R and len(R[code][2]) < 2):
            o = OPEN.get(code) or (R[code][0], R[code][1], "")
            for _ in range(2 - (len(R[code][2]) if code in R else 0)):
                out.append({"state": r["name"], "outlet": o[0], "name": "", "title": "open the staff page to fill", "read_from": o[1], "page": page, "hook": hook + "."})
    with open(os.path.join(HERE, "reporters_wave4.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    named = sum(1 for o in out if o["name"])
    md = ["| State | Outlet | Name | Title | Hook (their state page) |", "|---|---|---|---|---|"]
    for o in out:
        nm = f"[{o['name']}]({o['read_from']})" if o["name"] else f"[open staff page]({o['read_from']})"
        md.append(f"| {o['state']} | {o['outlet']} | {nm} | {o['title']} | [{o['hook']}]({o['page']}) |")
    open(os.path.join(HERE, "reporters_wave4.md"), "w").write("\n".join(md) + "\n")
    print(len(out), "rows,", named, "named")
