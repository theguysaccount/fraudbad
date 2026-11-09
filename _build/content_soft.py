# -*- coding: utf-8 -*-
"""Soft fraud: money lost to negligence rather than crime. Same rule as everything else:
every number has a source id in S, or it does not ship."""
import json, os
from content import S, TIERS, CASES

HERE = os.path.dirname(__file__)

S.update({
    "gao_ip_cum": ("GAO-25-108172: improper payments — about $2.8 trillion estimated since fiscal year 2003", "U.S. Government Accountability Office", "Mar 11, 2025", "https://www.gao.gov/products/GAO-25-108172"),
    "crfb_ma": ("New data suggests Medicare Advantage overpayments of $1.3 trillion over the next decade", "Committee for a Responsible Federal Budget", "Jan 23, 2026 (updated Mar 5, 2026)", "https://www.crfb.org/blogs/new-data-suggests-ma-overpayments-13-trillion-over-next-decade"),
    "jama": ("Waste in the US health care system: estimated costs and potential for savings (Shrank et al., JAMA)", "JAMA", "Oct 7, 2019", "https://doi.org/10.1001/jama.2019.13978"),
    "jama_pr": ("About one-quarter of U.S. health care spending is waste (study release)", "EurekAlert! / JAMA Network", "Oct 2019", "https://www.eurekalert.org/pub_releases/2019-10/jn-2ot100419.php"),
    "irs_gap": ("IR-2024-262: IRS releases 2022 tax gap projections", "Internal Revenue Service", "Oct 10, 2024", "https://www.irs.gov/newsroom/irs-releases-2022-tax-gap-projections-voluntary-compliance-rate-among-taxpayers-remains-steady"),
    "gao_weapons": ("GAO-26-108457: Weapon systems annual assessment", "U.S. Government Accountability Office", "Jul 2026", "https://www.gao.gov/products/gao-26-108457"),
    "dn_weapons": ("Pentagon's top new weapons programs are 12 years behind schedule: watchdog", "Defense News", "Jul 6, 2026", "https://www.defensenews.com/news/pentagon-congress/2026/07/06/pentagons-top-new-weapons-programs-are-12-years-behind-schedule-watchdog/"),
    "gao_dup": ("GAO identifies major opportunity: implementing open recommendations could deliver $132–251 billion in future savings", "U.S. Government Accountability Office", "May 12, 2026", "https://www.gao.gov/press-release/gao-identifies-major-opportunity-implementing-open-recommendations-could-deliver-132-251-billion-future-savings"),
    "gao_dup_rpt": ("GAO-26-108505: 2026 annual report on duplication, overlap and fragmentation", "U.S. Government Accountability Office", "May 2026", "https://www.gao.gov/products/GAO-26-108505"),
    "gao_it": ("GAO-25-107795: agencies need to continue addressing critical legacy systems", "U.S. Government Accountability Office", "Jul 17, 2025", "https://www.gao.gov/products/GAO-25-107795"),
    "nber_ye": ("Use-it-or-lose-it budget rules (Liebman & Mahoney, NBER Working Paper 19481)", "National Bureau of Economic Research", "Mar 2014", "https://www.nber.org/digest/mar14/use-it-or-lose-it-budget-rules"),
    "usas_signal": ("USAspending.gov award search: contracts with spending activity in FY2026, award value $2B+, top 100 by value", "USAspending.gov (U.S. Treasury), pulled by FraudBad", "Nov 9, 2026", "https://www.usaspending.gov/search"),
})

TIERS.update({
    "overrun": ("Over budget", "Officially measured cost growth or delay beyond what was promised."),
    "unfixed": ("Fix ignored", "A watchdog found the waste and the fix. The fix hasn't been made."),
})

# Every existing case gets a type. Hard = theft, deception, crimes, or an official fraud estimate.
# Soft = negligence: paid without proof, overpaid, can't account for it, or never collected it.
TYPE = {
    "federal-fraud-estimate": "hard", "pandemic-unemployment-fraud": "hard", "ppp-eidl-loan-fraud": "hard",
    "employee-retention-credit": "hard", "operation-gold-rush": "hard", "health-care-fraud-takedown-2026": "hard",
    "minnesota-medicaid-programs": "hard", "feeding-our-future": "hard", "arizona-sober-living-fraud": "hard",
    "california-unemployment-fraud": "hard", "michigan-unemployment-fraud": "hard", "washington-unemployment-theft": "hard",
    "mississippi-welfare-scandal": "hard", "los-angeles-hospice-fraud": "hard",
    "improper-payments-2025": "soft", "medicare-medicaid-no-receipts": "soft", "medicare-advantage-overpayments": "soft",
    "snap-payment-errors": "soft", "tax-credit-errors": "soft", "pentagon-failed-audits": "soft",
    "new-york-unemployment-overpayments": "soft", "los-angeles-homelessness-spending": "soft", "afghanistan-reconstruction": "soft",
}
TYPES = {
    "hard": ("Hard fraud", "Theft and deception: crimes, schemes, and official estimates of fraud."),
    "soft": ("Soft fraud", "Negligence: money paid without proof, paid too much, paid twice, lost track of, or never collected. No one has to break a law."),
}

# Medicare Advantage page: add the ten-year projection.
for c in CASES:
    if c["slug"] == "medicare-advantage-overpayments":
        c["receipt"].insert(1, ("Projected overpayments, 2027–2036", "$1.3 trillion", "crfb_ma"))
        c["happened"].append("Projected forward with the Congressional Budget Office's baseline, those overpayments come to about $1.3 trillion from 2027 through 2036: roughly $520 billion from coding and $760 billion from favorable selection, by the Committee for a Responsible Federal Budget's count.")
        c["sources"].insert(1, "crfb_ma")

# ------------------------------------------------------------- live contract signal
SIG = json.load(open(os.path.join(HERE, "data", "signal_contract_descriptions.json")))
BLANK = [f for f in SIG["flagged"] if f["kind"] in ("blank", "code")]
SHORT = [f for f in SIG["flagged"] if f["kind"] == "short"]
BLANK_TOTAL = sum(f["amount"] for f in BLANK)
SHORT_TOTAL = sum(f["amount"] for f in SHORT)
TOP_TOTAL = SIG["total"]

def _b(x):
    return f"${x/1e9:,.1f}B"

NEW_SOFT = [
    {
        "slug": "improper-payments-since-2003",
        "level": "federal", "place": "All reporting federal programs", "tier": "noproof", "type": "soft",
        "fig": "$2.8", "scale": "trillion since 2003",
        "title": "Paid out without proof, year after year",
        "dek": "Federal agencies have reported about $2.8 trillion in improper payments since 2003 — and $186 billion more in fiscal 2025 alone.",
        "sort": 2.8e12,
        "receipt": [
            ("Improper payments, FY2003–FY2024", "≈$2.8 trillion", "gao_ip_cum"),
            ("FY2024 alone", "$162B", "gao_ip_cum"),
            ("FY2025 alone", "$186B", "gao_ip"),
            ("Programs with no estimate at all", "TANF, Tenant-Based Rental Assistance, Shuttered Venue grants", "gao_ip_cum"),
        ],
        "redact": ("Recovered", "NO GOVERNMENT-WIDE TOTAL"),
        "happened": [
            "Since 2003, agencies have had to estimate how much they pay out wrongly or without the records to prove it. GAO put the running total at about $2.8 trillion through fiscal 2024.",
            "Fiscal 2025 added another $186 billion. Adding the two gives roughly $3 trillion. That sum is ours; GAO has not published a cumulative figure that includes 2025.",
        ],
        "missed": [
            "The total only counts programs that report. Temporary Assistance for Needy Families has never been included; HHS says it lacks the authority to get the data.",
            "A payment that can't be documented counts as improper, but it rarely gets clawed back. No one publishes a government-wide recovery total.",
        ],
        "sure": "These are the government's own estimates. Improper payments include errors and missing paperwork as well as fraud; GAO's separate fraud estimate is not comparable.",
        "sources": ["gao_ip_cum", "gao_ip"],
    },
    {
        "slug": "health-care-waste",
        "level": "federal", "place": "U.S. health care, public and private", "tier": "estimated", "type": "soft",
        "fig": "$760–935", "scale": "billion a year",
        "title": "Wasted in American health care every year",
        "dek": "About a quarter of all U.S. health spending is waste, a peer-reviewed estimate in JAMA found.",
        "sort": 935e9,
        "receipt": [
            ("Waste per year, all U.S. health care", "$760B–$935B", "jama_pr"),
            ("Share of total health spending", "About 25%", "jama_pr"),
            ("Administrative complexity", "$265.6B", "jama_pr"),
            ("Pricing failure (paying too much)", "$230.7B–$240.5B", "jama_pr"),
            ("Failure of care delivery", "$102.4B–$165.7B", "jama_pr"),
            ("Overtreatment and low-value care", "$75.7B–$101.2B", "jama_pr"),
            ("Fraud and abuse", "$58.5B–$83.9B", "jama_pr"),
            ("Failure of care coordination", "$27.2B–$78.2B", "jama_pr"),
        ],
        "redact": ("Taxpayers' share of the waste", "NOT ESTIMATED"),
        "happened": [
            "In 2019, researchers writing in JAMA added up six kinds of waste in U.S. health care and found $760 billion to $935 billion a year — about one dollar in four.",
            "Outright fraud was the smallest piece. Most of it was paperwork, prices nobody questions, and care that didn't help.",
        ],
        "missed": [
            "Most of this is legal. Nobody is charged for paying a price that's too high or for billing complexity.",
            "The study found proven fixes could cut $191 billion to $282 billion a year.",
        ],
        "sure": "A peer-reviewed estimate covering public and private health spending. Medicare and Medicaid pay a large share of U.S. health care, but the study did not split out the taxpayers' portion.",
        "sources": ["jama", "jama_pr"],
    },
    {
        "slug": "tax-gap",
        "level": "federal", "place": "Internal Revenue Service", "tier": "estimated", "type": "soft",
        "fig": "$696", "scale": "billion a year",
        "title": "Taxes owed that never get paid",
        "dek": "The IRS projects $696 billion in taxes went unpaid on time for 2022. After enforcement and late payments, $606 billion is projected to go uncollected.",
        "sort": 696e9,
        "receipt": [
            ("Gross tax gap, tax year 2022", "$696B", "irs_gap"),
            ("Net tax gap, after enforcement and late payments", "$606B", "irs_gap"),
            ("From underreported income", "$539B", "irs_gap"),
            ("From people who never filed", "$63B", "irs_gap"),
            ("From taxes reported but not paid", "$94B", "irs_gap"),
            ("Paid voluntarily and on time", "About 85%", "irs_gap"),
        ],
        "redact": ("Who owes it", "NOT PUBLISHED"),
        "happened": [
            "The IRS estimates how much tax should have been paid and wasn't. For tax year 2022, the latest projection, the gap was $696 billion. Enforcement and late payments bring it down to $606 billion, which the IRS projects will never be collected.",
            "Three-quarters of the gap comes from income that was never reported.",
        ],
        "missed": [
            "Underreported income makes up $539 billion of the $696 billion gap.",
        ],
        "sure": "An official IRS projection. The tax gap measures money owed and not paid; it is lost revenue, not spending.",
        "sources": ["irs_gap"],
    },
    {
        "slug": "weapons-cost-overruns",
        "level": "federal", "place": "Department of Defense", "tier": "overrun", "type": "soft",
        "fig": "$122", "scale": "billion in new cost growth",
        "title": "Weapons programs that went over budget this year",
        "dek": "In one year, 46 of the Pentagon's biggest weapons programs reported $122 billion in cost increases. The average new system now takes over 12 years to deliver.",
        "sort": 122e9,
        "receipt": [
            ("Planned spend on the costliest weapons programs", "Over $2.4 trillion", "dn_weapons"),
            ("Programs reporting cost increases", "46 of 72", "dn_weapons"),
            ("Total of those increases", "$122B", "dn_weapons"),
            ("Programs reporting decreases", "16, totaling $47B", "dn_weapons"),
            ("Average time to deliver a new capability", "Over 12 years", "dn_weapons"),
        ],
        "redact": ("Penalty for going over", "NONE REPORTED"),
        "happened": [
            "GAO's 2026 annual review of the Pentagon's major weapons programs found 46 of 72 programs reported cost increases totaling $122 billion, against $47 billion in decreases elsewhere.",
            "The department plans to spend more than $2.4 trillion on these programs. The average time to field a new capability rose to more than 12 years.",
        ],
        "missed": [
            "Cost growth is reported every year, and the programs continue.",
        ],
        "sure": "Measured by GAO from the Pentagon's own program data. Cost growth isn't fraud; it's money spent beyond what Congress was told.",
        "sources": ["gao_weapons", "dn_weapons"],
    },
    {
        "slug": "unfixed-gao-savings",
        "level": "federal", "place": "Congress and federal agencies", "tier": "unfixed", "type": "soft",
        "fig": "$132–251", "scale": "billion left on the table",
        "title": "Savings the government's auditors found — and nobody took",
        "dek": "GAO says acting on its open recommendations could save $132 billion to $251 billion. Past action on its findings has saved $774 billion since 2011.",
        "sort": 251e9,
        "receipt": [
            ("Future savings from open recommendations", "$132B–$251B", "gao_dup"),
            ("Saved since 2011 by acting on GAO's findings", "≈$774B", "gao_dup"),
            ("New recommendations in 2026", "97", "gao_dup"),
            ("One fix: equal Medicare rates for office visits", "$156.9B over 10 years", "gao_dup"),
        ],
        "redact": ("Date the rest gets fixed", "NONE SET"),
        "happened": [
            "Every year GAO publishes a report on programs that overlap, duplicate each other, or waste money, with a fix for each. Its May 2026 report added 97 new recommendations.",
            "GAO estimates that acting on the open ones could save $132 billion to $251 billion. One example: paying Medicare the same rate for an office visit no matter where it happens would save $156.9 billion over 10 years.",
        ],
        "missed": [
            "Each fix needs an agency or Congress to act, and GAO counts the ones still open every year.",
        ],
        "sure": "GAO's own savings estimates. The $774 billion already saved shows the method works when someone acts on it.",
        "sources": ["gao_dup", "gao_dup_rpt"],
    },
    {
        "slug": "federal-it-legacy-systems",
        "level": "federal", "place": "Federal agencies", "tier": "unfixed", "type": "soft",
        "fig": "$100", "scale": "billion+ a year",
        "title": "Federal tech money spent keeping old systems alive",
        "dek": "The government spends over $100 billion a year on IT, and agencies typically put about 80% of it into running what they already have.",
        "sort": 100e9,
        "receipt": [
            ("Federal IT spending per year", "Over $100B", "gao_it"),
            ("Share spent operating existing systems", "About 80%", "gao_it"),
            ("Critical legacy systems GAO flagged in 2019", "10", "gao_it"),
            ("Of those, modernized by Feb 2025", "3", "gao_it"),
            ("With no planned completion date", "1", "gao_it"),
        ],
        "redact": ("Cost to keep the old ones running", "NOT TOTALED"),
        "happened": [
            "GAO flagged 10 of the government's most critical legacy computer systems in 2019. By February 2025, agencies had modernized three. One still had no planned completion date.",
            "Agencies typically report spending about 80 percent of their IT budgets on operating and maintaining existing systems.",
        ],
        "missed": [
            "Seven of the ten critical systems GAO flagged in 2019 were still waiting to be modernized in February 2025.",
        ],
        "sure": "GAO's figures from agency reporting. Not all maintenance is waste; the point is how little goes to replacing what's failing.",
        "sources": ["gao_it"],
    },
    {
        "slug": "contracts-with-no-description",
        "level": "federal", "place": "USAspending.gov", "tier": "unauditable", "type": "soft",
        "fig": _b(BLANK_TOTAL).replace("B", ""), "scale": "billion with no description",
        "title": "Giant contracts the public can't read",
        "dek": f"{len(BLANK)} of the 100 biggest federal contracts active in fiscal 2026 — worth {_b(BLANK_TOTAL)} — list no description at all, or only a filing code.",
        "sort": BLANK_TOTAL,
        "receipt": [
            ("Biggest contracts active in FY2026, checked", "100 (worth " + _b(TOP_TOTAL) + ")", "usas_signal"),
            ("Description blank", str(sum(1 for f in BLANK if f['kind'] == 'blank')), "usas_signal"),
            ("Description is only a filing code", str(sum(1 for f in BLANK if f['kind'] == 'code')), "usas_signal"),
            ("Value of those contracts", _b(BLANK_TOTAL), "usas_signal"),
            ("Three words or fewer", f"{len(SHORT)} more ({_b(SHORT_TOTAL)})", "usas_signal"),
        ],
        "redact": ("What the money buys", "NOT PUBLISHED"),
        "happened": [
            f"We pulled the 100 largest federal contracts that had spending activity in fiscal 2026 from USAspending.gov, the government's own spending site. Together they're worth {_b(TOP_TOTAL)}.",
            f"{len(BLANK)} of them, worth {_b(BLANK_TOTAL)}, show either a blank description or only an internal code like \"IGF::OT::IGF.\" Another {len(SHORT)}, worth {_b(SHORT_TOTAL)}, say three words or fewer.",
        ],
        "missed": [
            "Agencies enter these descriptions themselves. No rule holds up a payment when the field is blank.",
            "The full list, with links to every award, is on the Soft Fraud page.",
        ],
        "sure": "Measured by FraudBad from USAspending.gov on November 9, 2026. A blank description is not proof of waste; it means the public can't tell what was bought. Award values are lifetime totals for awards with activity in fiscal 2026.",
        "sources": ["usas_signal"],
    },
]
for c in NEW_SOFT:
    TYPE[c["slug"]] = c["type"]
for c in CASES:
    c["type"] = TYPE[c["slug"]]
CASES.extend(NEW_SOFT)

SOFT_BIG = [
    ("$2.8T", "paid without proof since 2003", "improper-payments-since-2003", "gao_ip_cum"),
    ("$1.3T", "projected Medicare Advantage overpayments, 2027–2036", "medicare-advantage-overpayments", "crfb_ma"),
    ("$760–935B", "a year wasted in U.S. health care", "health-care-waste", "jama_pr"),
    ("$696B", "a year in taxes owed and not paid on time", "tax-gap", "irs_gap"),
    ("$132–251B", "in savings GAO found that nobody has taken", "unfixed-gao-savings", "gao_dup"),
    (_b(BLANK_TOTAL), "in top contracts with no description", "contracts-with-no-description", "usas_signal"),
]

SIGNALS = [
    ("01", "Paid without proof", "Look for payments that went out without the records to show they were right.",
     "Agency improper-payment estimates and their \"insufficient documentation\" share; CMS error-rate reports.",
     "Share of dollars paid without documentation.", ["medicare-medicaid-no-receipts", "improper-payments-since-2003"]),
    ("02", "Paid more than everyone else", "Compare what one buyer paid with what others paid for the same thing.",
     "Unit prices on federal orders (the RECEIPTS Act would publish these), inspector-general price audits, MedPAC's Medicare Advantage vs. traditional Medicare comparison.",
     "Price paid ÷ median price for the same item.", ["medicare-advantage-overpayments"]),
    ("03", "Over budget, behind schedule", "Compare today's cost and date with what was promised.",
     "GAO's annual weapons assessment, the federal IT Dashboard, state and city capital-project audits.",
     "Current cost estimate ÷ original baseline; years of delay.", ["weapons-cost-overruns", "federal-it-legacy-systems"]),
    ("04", "Paying twice", "Find programs that do the same job for the same people.",
     "GAO's annual duplication, overlap and fragmentation report and its open recommendations.",
     "Dollars in overlapping programs; GAO's estimated savings.", ["unfixed-gao-savings"]),
    ("05", "Owed and never collected", "Count money the government is owed and never gets.",
     "IRS tax gap projections; uncollected overpayment balances in agency financial reports.",
     "Money owed minus money collected.", ["tax-gap"]),
    ("06", "Can't show where it went", "Find spending nobody can trace or explain.",
     "Failed financial audits, USAspending.gov fields left blank, local audits that can't match spending to results.",
     "Dollars with no traceable recipient, purpose or result.", ["contracts-with-no-description", "pentagon-failed-audits", "los-angeles-homelessness-spending"]),
    ("07", "Spend it or lose it", "Watch for spending rushed out before the money expires.",
     "Contract action dates on USAspending.gov. Research found agencies spend 4.9 times a normal week's amount in the last week of the fiscal year, and last-week IT projects were 2 to 6 times more likely to be rated lower quality.",
     "Last-week share of annual spending vs. 1/52 of the year.", []),
]
