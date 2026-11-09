# -*- coding: utf-8 -*-
"""Round 3: the government's own improper-payment ledger, the September rush, and the cases found by
working the rest of the search plan. Same rule: every number has a source id in S, or it does not ship."""
import json, os
from content import S, TIERS, CASES
import content_soft
from content_soft import TYPE, SOFT_BIG, SIGNALS

HERE = os.path.dirname(__file__)

S.update({
    "pa_data": ("FY2025 improper payments dataset: every program's results, root causes, recoveries and compliance (FY2004–FY2025)", "PaymentAccuracy.gov (OMB and CFO Council); totals summed by FraudBad", "Nov 9, 2026", "https://paymentaccuracy.gov/assets/files/FY2025_Dataset.xlsx"),
    "pa_site": ("Agencies & programs: improper payment rates, FY2025", "PaymentAccuracy.gov", "accessed Nov 9, 2026", "https://www.paymentaccuracy.gov/agencies-and-programs"),
    "omb_m2119": ("M-21-19: Appendix C to Circular A-123, Requirements for Payment Integrity Improvement (root-cause definitions, Table 3)", "Office of Management and Budget", "Mar 5, 2021", "https://www.whitehouse.gov/wp-content/uploads/2021/03/M-21-19.pdf"),
    "gao_cfs": ("GAO-26-108073: audit of the FY2025 and FY2024 consolidated financial statements of the U.S. government", "U.S. Government Accountability Office", "Mar 19, 2026", "https://www.gao.gov/products/GAO-26-108073"),
    "usas_month": ("USAspending.gov spending-over-time data: federal contract obligations by fiscal month, FY2018–FY2025", "USAspending.gov (U.S. Treasury), pulled by FraudBad", "Nov 9, 2026", "https://www.usaspending.gov/search"),
    "doj_fca": ("False Claims Act settlements and judgments exceed $6.8B in fiscal year 2025", "U.S. Department of Justice", "Jan 16, 2026", "https://www.justice.gov/opa/pr/false-claims-act-settlements-and-judgments-exceed-68b-fiscal-year-2025"),
    "route50_snap": ("Agriculture focuses on SNAP fraud, while experts worry EBT theft will go unabated", "Route Fifty", "Dec 23, 2025", "https://www.route-fifty.com/digital-government/2025/12/agriculture-focuses-snap-fraud-while-experts-worry-ebt-theft-will-go-unabated/410362"),
    "treas_debt24": ("U.S. Government Receivables and Debt Collection Activities of Federal Agencies, FY2024 report to Congress", "U.S. Department of the Treasury, Bureau of the Fiscal Service", "FY2024 report", "https://fiscal.treasury.gov/files/debt-management/debt24.pdf"),
    "govexec_ssa": ("New Social Security report shows growing overpayment problem tops $23B", "Government Executive", "Nov 2023", "https://www.govexec.com/oversight/2023/11/new-social-security-report-shows-growing-overpayment-problem-tops-23b/392143/"),
    "ssa_oig": ("Audit 072301: processing Old-Age, Survivors and Disability Insurance overpayments", "Social Security Administration Office of the Inspector General", "Sep 30, 2025", "https://www.oversight.gov/sites/default/files/documents/reports/2026-07/072301.pdf"),
    "fnn_sentinel": ("DoD's troubled Sentinel program will continue despite ballooning costs", "Federal News Network", "Jul 2024", "https://federalnewsnetwork.com/defense-main/2024/07/dods-troubled-sentinel-program-will-continue-despite-ballooning-costs/"),
    "ktvu_hsr": ("California high-speed rail costs soar to $231 billion", "KTVU Fox 2", "Apr 30, 2026", "https://www.ktvu.com/news/california-high-speed-rail-cost-soars-231-billion"),
    "kalw_hsr": ("High-speed rail business plan approved, envisions passenger service by 2033", "KALW", "Jun 3, 2026", "https://www.kalw.org/bay-area-news/2026-06-03/high-speed-rail-business-plan-approved-envisions-passenger-service-by-2033"),
    "ra_hsr": ("CHSRA issues draft 2026 business plan", "Railway Age", "2026 (on the Feb 28, 2026 draft)", "https://www.railwayage.com/passenger/high-performance/chsra-issues-draft-2026-business-plan/"),
    "civilbeat_hart": ("Cost of Honolulu rail line may be climbing again", "Honolulu Civil Beat", "Aug 5, 2026", "https://www.civilbeat.org/2026/08/cost-of-honolulu-rail-line-may-be-climbing-again/"),
    "medecon_cuban": ("Medicare could save billions buying generics through Mark Cuban prescription drug company (on Lalani et al., Annals of Internal Medicine)", "Medical Economics", "Jun 2022", "https://www.medicaleconomics.com/view/medicare-could-save-billions-buying-generics-through-mark-cuban-prescription-drug-company"),
})

TIERS.update({
    "measured": ("Measured", "FraudBad counted it ourselves from official government data. The page shows the query and links to the data."),
    "uncollected": ("Never collected", "Money the government is owed and hasn't collected, by its own count."),
})

# ------------------------------------------------------------------ the ledger (official dataset)
L = json.load(open(os.path.join(HERE, "data", "ledger_fy2025.json")))
YEARS = {int(k): v for k, v in L["years"].items()}
PROGS = L["programs_2025"]
RC = L["root_causes_2025_m"]
REC = {int(k): v for k, v in L["recovery_m"].items()}
NONCOMP = L["compliance_fy2024"]["noncompliant"]
N_AGENCIES = L["compliance_fy2024"]["rated"]
FY25 = YEARS[2025]["amount_m"] * 1e6
CUM = L["cumulative_m"] * 1e6
CUM24 = L["cum_through_2024_m"] * 1e6
FIRST_YEAR = min(YEARS)
RC_FAIL = RC["Failure to Access Data/Information Needed"] * 1e6
RC_NOEXIST = RC["Data/Information Needed Does Not Exist"] * 1e6
RC_DOCS = RC["Insufficient Documentation to Determine"] * 1e6
RC_INAB = RC["Inability to Access the Data/Information"] * 1e6
RC_TECH = [v for k, v in RC.items() if k.startswith("Technically")][0] * 1e6
REC25 = REC[2025]
OVER10 = sum(1 for p in PROGS if p["rate"] and p["rate"] >= 0.10)
OVER25 = sum(1 for p in PROGS if p["rate"] and p["rate"] >= 0.25)
AGENCY_NAMES = {
    "HHS": "Health and Human Services", "Treasury": "Treasury", "USDA": "Agriculture", "SBA": "Small Business Administration",
    "SSA": "Social Security", "DOL": "Labor", "HUD": "Housing and Urban Development", "DOT": "Transportation", "VA": "Veterans Affairs",
    "DOW": "Defense (War)", "ED": "Education", "OPM": "Personnel Management", "DHS": "Homeland Security", "DOJ": "Justice",
    "DOE": "Energy", "DOI": "Interior", "DOS": "State", "EPA": "EPA", "GSA": "GSA", "NASA": "NASA", "NSF": "NSF", "RRB": "Railroad Retirement Board",
    "USAID": "USAID", "CNCS": "AmeriCorps", "FCC": "FCC", "EAC": "Election Assistance Commission", "SSS": "Selective Service",
    "DOC": "Commerce", "NRC": "Nuclear Regulatory Commission", "SEC": "SEC", "PBGC": "PBGC", "SI": "Smithsonian",
}


def agency(a):
    return AGENCY_NAMES.get(a, a)


def _bn(m, d=1):
    """$ millions -> '$X.XB'"""
    return f"${m/1000:,.{d}f}B"


def _prog(name):
    for p in PROGS:
        if name in p["program"]:
            return p
    raise KeyError(name)


SVOG = _prog("Shuttered Venue")
PBRA = _prog("Project Based Rental Assistance")
PBRA_PREV_UNKNOWN_M = 45.24  # FY2024 unknown payments for the same program, from the same dataset
assert max(PROGS, key=lambda p: p["rate"] or 0)["program"] == SVOG["program"], "SVOG must have the highest combined rate"

# ------------------------------------------------------------------ September rush (USAspending)
MON = json.load(open(os.path.join(HERE, "data", "contracts_by_month.json")))
RUSH = {}
for fy, ms in MON.items():
    ms = sorted([m for m in ms if m["time_period"]["fiscal_year"] == fy], key=lambda m: int(m["time_period"]["month"]))
    if len(ms) != 12 or int(fy) > 2025:
        continue
    tot = sum(m["aggregated_amount"] for m in ms)
    sep = ms[-1]["aggregated_amount"]
    RUSH[int(fy)] = {"total": tot, "sep": sep, "share": sep / tot, "x": sep / ((tot - sep) / 11),
                     "biggest": max(ms, key=lambda m: m["aggregated_amount"]) is ms[-1]}
assert all(r["biggest"] for r in RUSH.values()), "September must be the biggest month every year we claim it"
R25 = RUSH[2025]
RUSH_YEARS = sorted(RUSH)
RUSH_MIN = min(r["share"] for r in RUSH.values())
RUSH_MAX = max(r["share"] for r in RUSH.values())
RUSH_SEP_TOTAL = sum(r["sep"] for r in RUSH.values())


def _pct(x, d=1):
    return f"{x*100:.{d}f}%"


NEW = [
    {
        "slug": "data-existed-nobody-checked",
        "level": "federal", "place": "All reporting federal programs", "tier": "noproof", "type": "soft",
        "fig": f"${RC_FAIL/1e9:,.0f}", "scale": "billion paid wrong",
        "title": "The data to stop it existed. Nobody checked.",
        "dek": f"Two-thirds of the government's {_bn(FY25/1e6)} in improper payments in fiscal 2025 happened because the agency didn't check information it already had access to — by the government's own count.",
        "sort": RC_FAIL,
        "receipt": [
            ("Improper and unverifiable payments, FY2025", _bn(FY25/1e6), "pa_data"),
            ("Data existed and was accessible; not checked", _bn(RC_FAIL/1e6), "pa_data"),
            ("Data existed; agency couldn't get it", _bn(RC_INAB/1e6), "pa_data"),
            ("Data needed didn't exist", _bn(RC_NOEXIST/1e6), "pa_data"),
            ("Not enough paperwork to tell either way", _bn(RC_DOCS/1e6), "pa_data"),
            ("Right amount, rules not followed", _bn(RC_TECH/1e6), "pa_data"),
            ("Agencies out of compliance with the payment-integrity law, FY2024", f"{len(NONCOMP)} of {N_AGENCIES}", "pa_data"),
        ],
        "redact": ("Which payments, to whom", "NOT PUBLISHED"),
        "happened": [
            "Every federal program that reports improper payments has to say why they happened, using categories set by the Office of Management and Budget.",
            f"The biggest category is \"failure to access data.\" OMB defines it as errors made even though the information needed to check the payment \"exists and is accessible\" to the agency. In fiscal 2025 that category alone was {_bn(RC_FAIL/1e6)} — {RC_FAIL/FY25*100:.0f}% of the total.",
        ],
        "missed": [
            f"{len(NONCOMP)} of the {N_AGENCIES} agencies tracked were out of compliance with the Payment Integrity Information Act in fiscal 2024, including Health and Human Services, Treasury, Social Security, Agriculture, Defense, Veterans Affairs, HUD, SBA and Labor.",
            f"In fiscal 2025 agencies flagged {_bn(REC25['identified_m'])} in overpayments to claw back and recovered {_bn(REC25['recovered_m'])}.",
        ],
        "sure": "Root causes are reported by each agency to OMB. FraudBad summed them from the official FY2025 dataset; the total matches the $186 billion GAO reports. These describe errors, not intent.",
        "sources": ["pa_data", "omb_m2119", "gao_ip"],
    },
    {
        "slug": "september-spending-rush",
        "level": "federal", "place": "Every federal agency that buys things", "tier": "measured", "type": "soft",
        "fig": f"${R25['sep']/1e9:,.0f}", "scale": "billion in one month",
        "title": "The September rush: spend it before it expires",
        "dek": f"Agencies signed {_bn(R25['sep']/1e6)} in contracts in September 2025 — {_pct(R25['share'])} of the year's contract money in the last month, {R25['x']:.1f} times an average month.",
        "sort": R25["sep"],
        "receipt": [
            ("Contract obligations, FY2025", _bn(R25["total"]/1e6), "usas_month"),
            ("September 2025 alone", _bn(R25["sep"]/1e6), "usas_month"),
            ("Share of the year", f"{_pct(R25['share'])} (an even month: 8.3%)", "usas_month"),
            ("Versus an average October–August month", f"{R25['x']:.1f}×", "usas_month"),
            (f"September's share, FY{RUSH_YEARS[0]}–FY{RUSH_YEARS[-1]}", f"{_pct(RUSH_MIN)}–{_pct(RUSH_MAX)}", "usas_month"),
            (f"Years September was the biggest month", f"{len(RUSH)} of {len(RUSH)}", "usas_month"),
            ("Last-week IT projects rated lower quality", "2–6× more likely", "nber_ye"),
        ],
        "redact": ("Why each contract was signed in September", "NOT RECORDED"),
        "happened": [
            f"The federal fiscal year ends September 30, and one-year money that isn't committed by then can no longer be used for new contracts. We pulled every month of federal contract obligations from USAspending.gov for fiscal {RUSH_YEARS[0]} through {RUSH_YEARS[-1]}.",
            f"September was the biggest month in all {len(RUSH)} years. In fiscal 2025 agencies obligated {_bn(R25['sep']/1e6)} in September — {_pct(R25['share'])} of the year — against an average of {_bn((R25['total']-R25['sep'])/11/1e6)} in each of the other eleven months.",
        ],
        "missed": [
            "Economists Jeffrey Liebman and Neale Mahoney found agencies spend 4.9 times a normal week's amount in the last week of the year, and that last-week IT projects were 2 to 6 times more likely to be rated lower quality.",
            "USAspending shows when a contract was signed, not why. Nothing in the public record explains the timing.",
        ],
        "sure": "Measured by FraudBad from USAspending.gov contract obligations by fiscal month (October is month 1). A September spike isn't proof of waste; some contracts are timed to the budget cycle for good reasons. Fiscal 2026 isn't shown because its last months are still being reported.",
        "sources": ["usas_month", "nber_ye"],
    },
    {
        "slug": "shuttered-venue-grants",
        "level": "federal", "place": "Small Business Administration", "tier": "noproof", "type": "soft",
        "fig": _bn(SVOG["total_m"]).replace("B", "").replace("$", "$"), "scale": "billion paid wrong or unproven",
        "title": "Venue grants: 69% paid wrong or without proof",
        "dek": f"SBA's Shuttered Venue Operators Grants show {_bn(SVOG['outlays_m'])} in payments. In fiscal 2025, SBA counted {_bn(SVOG['improper_m'],2)} as improper and {_bn(SVOG['unknown_m'],2)} it couldn't verify — {_pct(SVOG['rate'])} of the money, the highest rate of any program that reported.",
        "sort": SVOG["total_m"] * 1e6,
        "receipt": [
            ("Payments reviewed", _bn(SVOG["outlays_m"]), "pa_data"),
            ("Improper", _bn(SVOG["improper_m"], 2), "pa_data"),
            ("Can't tell either way (no documentation)", _bn(SVOG["unknown_m"], 2), "pa_data"),
            ("Wrong or unverifiable", _pct(SVOG["rate"]), "pa_data"),
            ("Rank among 64 programs reporting", "#1 by error rate", "pa_data"),
        ],
        "redact": ("Grantees paid improperly", "NOT PUBLISHED"),
        "happened": [
            "The Shuttered Venue Operators Grant was SBA's pandemic relief program for live-event venues, theaters and museums.",
            f"When SBA measured the program for its fiscal 2025 payment-integrity report, it found {_bn(SVOG['improper_m'],2)} in improper payments and {_bn(SVOG['unknown_m'],2)} it couldn't prove right or wrong — together {_pct(SVOG['rate'])} of {_bn(SVOG['outlays_m'])}.",
        ],
        "missed": [
            "The money went out during the pandemic. The error rate was measured years later, after it was spent.",
            "SBA was one of the agencies out of compliance with the federal payment-integrity law in fiscal 2024.",
        ],
        "sure": "SBA's own estimate, reported to OMB in the official FY2025 dataset. Improper payments include errors and missing paperwork, not only fraud.",
        "sources": ["pa_data", "pa_site", "gao_ip"],
    },
    {
        "slug": "hud-rental-assistance-unverified",
        "level": "federal", "place": "Department of Housing and Urban Development", "tier": "unauditable", "type": "soft",
        "fig": _bn(PBRA["unknown_m"], 2).replace("B", ""), "scale": "billion HUD can't verify",
        "title": "Rent subsidies HUD can't verify",
        "dek": f"In fiscal 2025, HUD said it couldn't determine whether {_bn(PBRA['unknown_m'],2)} of its project-based rental assistance — {_pct(PBRA['rate'])} of the program — was paid correctly. A year earlier the figure was $45 million.",
        "sort": PBRA["unknown_m"] * 1e6,
        "receipt": [
            ("Program payments reviewed, FY2025", _bn(PBRA["outlays_m"], 2), "pa_data"),
            ("Payments HUD can't verify", _bn(PBRA["unknown_m"], 2), "pa_data"),
            ("Share of the program", _pct(PBRA["rate"]), "pa_data"),
            ("Same measure, FY2024", f"${PBRA_PREV_UNKNOWN_M:,.0f}M (0.3%)", "pa_data"),
            ("Improper payments it confirmed", "$0", "pa_data"),
        ],
        "redact": ("Which properties got the unverified money", "NOT PUBLISHED"),
        "happened": [
            "HUD's project-based rental assistance pays private owners to keep apartments affordable for low-income tenants.",
            f"In its fiscal 2025 report HUD put {_bn(PBRA['unknown_m'],2)} in the \"unknown\" column: payments it couldn't prove right or wrong because the documentation wasn't there. In fiscal 2024 the same column held $45 million.",
        ],
        "missed": [
            "HUD was one of the agencies out of compliance with the federal payment-integrity law in fiscal 2024.",
        ],
        "sure": "HUD's own figures in the official FY2025 dataset. \"Unknown\" means insufficient documentation, not proven fraud. The jump from fiscal 2024 may partly reflect a change in how HUD tested payments; the dataset doesn't say.",
        "sources": ["pa_data", "pa_site"],
    },
    {
        "slug": "federal-debt-never-collected",
        "level": "federal", "place": "Every federal agency owed money", "tier": "uncollected", "type": "soft",
        "fig": "$217", "scale": "billion owed and overdue",
        "title": "Money owed to the government that it isn't collecting",
        "dek": "By the end of fiscal 2024, people and businesses owed federal agencies $217.3 billion in overdue non-tax debt. That year agencies collected $21.5 billion of overdue debt and wrote off $57.7 billion.",
        "sort": 217.3e9,
        "receipt": [
            ("Non-tax money owed to agencies", "$2.36 trillion", "treas_debt24"),
            ("Overdue", "$217.3B", "treas_debt24"),
            ("Overdue more than two years", "$156.2B (72%)", "treas_debt24"),
            ("Overdue debt collected in FY2024", "$21.5B", "treas_debt24"),
            ("Written off or closed out in FY2024", "$57.7B", "treas_debt24"),
            ("Education", "$145.1B overdue", "treas_debt24"),
            ("Small Business Administration", "$32.3B overdue", "treas_debt24"),
            ("Social Security", "$6.9B overdue", "treas_debt24"),
        ],
        "redact": ("Biggest debtors, by name", "NOT PUBLISHED"),
        "happened": [
            "Every year Treasury reports what federal agencies are owed outside of taxes: student loans, small-business and disaster loans, benefit overpayments, fines and fees.",
            "By September 30, 2024, $217.3 billion of it was overdue, and 72% had been overdue for more than two years.",
        ],
        "missed": [
            "Most of the overdue balance sits at Education ($145.1 billion) and SBA ($32.3 billion).",
            "In fiscal 2024 agencies wrote off or closed out $57.7 billion — more than two and a half times the $21.5 billion in overdue debt they collected.",
        ],
        "sure": "Treasury's own count, from agency reports. Overdue debt is money owed, not money stolen, and some of it will still be collected.",
        "sources": ["treas_debt24"],
    },
    {
        "slug": "social-security-overpayments",
        "level": "federal", "place": "Social Security Administration", "tier": "uncollected", "type": "soft",
        "fig": "$23", "scale": "billion not yet recovered",
        "title": "Social Security overpayments that haven't come back",
        "dek": "Social Security reported $23 billion in uncollected overpayments at the start of fiscal 2024. Its inspector general later found SSA booked about $904 million as recovered that wasn't.",
        "sort": 23e9,
        "receipt": [
            ("Uncollected overpayments, Oct 1, 2023", "$23B", "govexec_ssa"),
            ("A year earlier", "$21.6B", "govexec_ssa"),
            ("New overpayments, FY2022", "About $11.1B", "govexec_ssa"),
            ("Of those, caused by SSA, not the recipient", "About $1.9B", "govexec_ssa"),
            ("Retirement and disability overpayments, FY2022–23", "Almost $10B", "ssa_oig"),
            ("Booked as recovered, but wasn't", "About $904M", "ssa_oig"),
            ("Miscalculated, mostly never to be recovered", "Almost $245M", "ssa_oig"),
        ],
        "redact": None,
        "happened": [
            "When Social Security pays someone more than they're owed, it's supposed to get the money back, usually by holding back future benefits. The unpaid balance reached $23 billion by October 1, 2023, up from $21.6 billion a year earlier.",
            "In September 2025 SSA's inspector general reviewed the retirement and disability overpayments SSA recorded in fiscal 2022 and 2023 — almost $10 billion. It found about $904 million recorded as recovered through benefit withholding that hadn't been, and nearly 35,000 overpayments, worth almost $245 million, calculated wrong.",
        ],
        "missed": [
            "The inspector general said most of the miscalculated overpayments hadn't been spotted by SSA and won't be recovered.",
            "About $1.9 billion of fiscal 2022's new overpayments were caused by SSA, not the people who received them.",
        ],
        "sure": "SSA's own financial report and its inspector general's audit. Overpayments are mostly errors, often SSA's; many people who were overpaid did nothing wrong.",
        "sources": ["govexec_ssa", "ssa_oig"],
    },
    {
        "slug": "snap-card-skimming",
        "level": "federal", "place": "SNAP, run by the states for USDA", "tier": "confirmed", "type": "hard",
        "fig": "$320", "scale": "million stolen and replaced",
        "title": "Food benefits skimmed straight off EBT cards",
        "dek": "Thieves skimmed SNAP benefits off families' cards. USDA replaced $320 million from October 2022 to December 2024. Then federal replacement stopped, and so did USDA's count.",
        "sort": 320e6,
        "receipt": [
            ("Stolen benefits USDA replaced, Oct 2022–Dec 20, 2024", "$320M", "route50_snap"),
            ("Federal replacements after Dec 20, 2024", "Not funded", "route50_snap"),
            ("Stolen Jan–Jun 2025 (Propel estimate, not USDA)", "$349M", "route50_snap"),
            ("States that moved to chip cards", "1 (California)", "route50_snap"),
            ("Counterfeit EBT terminals blocked by USDA", "450+", "route50_snap"),
        ],
        "redact": ("USDA's count of thefts since 2024", "NO LONGER COLLECTED"),
        "happened": [
            "Skimmers copy the magnetic stripe on a SNAP card at the checkout and drain the account. USDA replaced $320 million in stolen benefits between October 2022 and December 20, 2024.",
            "After that, Congress stopped funding federal replacements and USDA stopped collecting the data. A benefits-app company, Propel, estimates $349 million was stolen in the first half of 2025 alone.",
        ],
        "missed": [
            "Congress asked USDA in late 2022 to move states to chip cards through rulemaking. It hasn't. Only California has switched.",
        ],
        "sure": "The $320 million is USDA's own replacement total, which undercounts theft. The 2025 figure is a private estimate. Stealing from families is a crime, so this is hard fraud.",
        "sources": ["route50_snap"],
    },
    {
        "slug": "false-claims-act-2025",
        "level": "federal", "place": "Department of Justice", "tier": "settled", "type": "hard",
        "fig": "$6.8", "scale": "billion clawed back, a record",
        "title": "What the government won back from fraud in court",
        "dek": "The Justice Department recovered more than $6.8 billion under the False Claims Act in fiscal 2025, its highest ever. Measured against GAO's fraud estimate, that's 1 to 3 cents on the dollar.",
        "sort": 6.8e9,
        "receipt": [
            ("Settlements and judgments, FY2025", "Over $6.8B", "doj_fca"),
            ("From health care fraud", "Over $5.7B", "doj_fca"),
            ("Whistleblower suits filed", "1,297", "doj_fca"),
            ("Investigations DOJ opened on its own", "401", "doj_fca"),
            ("Recovered since 1986", "Over $85B", "doj_fca"),
            ("Versus one year of estimated fraud ($233B–$521B)", "1.3%–2.9%", "gao_fraud"),
        ],
        "redact": ("Fraud that was never caught", "UNCOUNTED"),
        "happened": [
            "The False Claims Act lets the government, and whistleblowers, sue anyone who cheats a federal program.",
            "In the year ending September 30, 2025, settlements and judgments topped $6.8 billion, more than $5.7 billion of it from health care. Whistleblowers filed 1,297 new suits.",
        ],
        "missed": [
            "Since 1986 the act has brought back more than $85 billion in total — less than GAO's low estimate of what fraud costs in a single year.",
        ],
        "sure": "DOJ's own figures. The comparison with GAO's fraud estimate is our arithmetic. Most recoveries are settlements, which usually don't include an admission of wrongdoing.",
        "sources": ["doj_fca", "gao_fraud"],
    },
    {
        "slug": "sentinel-icbm-overrun",
        "level": "federal", "place": "U.S. Air Force", "tier": "overrun", "type": "soft",
        "fig": "$141", "scale": "billion, 81% over estimate",
        "title": "The nuclear missile that's 81% over budget",
        "dek": "The Air Force's Sentinel ICBM is now estimated at $140.9 billion, 81% more than projected in 2020. That triggered the law for runaway weapons costs. The Pentagon kept it going.",
        "sort": 140.9e9,
        "receipt": [
            ("Current cost estimate", "$140.9B", "fnn_sentinel"),
            ("Growth over the September 2020 estimate", "81%", "fnn_sentinel"),
            ("Overrun that triggered the legal review", "37%", "fnn_sentinel"),
            ("Threshold in the law", "25%", "fnn_sentinel"),
            ("Outcome", "Program continues", "fnn_sentinel"),
        ],
        "redact": ("Final cost", "NOT KNOWN YET"),
        "happened": [
            "Sentinel is the Air Force's replacement for its Minuteman III intercontinental ballistic missiles.",
            "In July 2024 the Defense Department said Sentinel's cost had grown 81% over its September 2020 estimate, to $140.9 billion. The overrun set off a Nunn-McCurdy review, the process Congress set up for weapons programs whose costs run away.",
        ],
        "missed": [
            "A program that breaches Nunn-McCurdy this badly is supposed to be canceled unless the Pentagon certifies it's essential. The Pentagon certified Sentinel and kept it going.",
        ],
        "sure": "The Pentagon's own figures, as reported by Federal News Network. Cost growth isn't fraud; it's money beyond what Congress was told.",
        "sources": ["fnn_sentinel"],
    },
    {
        "slug": "california-high-speed-rail",
        "level": "state", "place": "California High-Speed Rail Authority", "tier": "overrun", "type": "soft",
        "fig": "$126–231", "scale": "billion, from $33B promised",
        "title": "California's bullet train: $33 billion promised, up to $231 billion now",
        "dek": "Voters approved high-speed rail in 2008 at a price of about $33 billion, done by 2020. The 2026 business plan puts San Francisco to Los Angeles at $126 billion to $231 billion. The first passengers ride in 2033, on the Central Valley segment.",
        "sort": 231e9,
        "receipt": [
            ("Price voters approved, 2008", "$33B", "ktvu_hsr"),
            ("Promised completion", "2020", "ktvu_hsr"),
            ("2026 estimate, San Francisco–L.A./Anaheim", "$126B–$231B", "kalw_hsr"),
            ("Merced–Bakersfield segment alone", "$34.76B", "ra_hsr"),
            ("First passenger service (Merced–Bakersfield)", "2033", "kalw_hsr"),
            ("Still to be secured", "Nearly $87B", "kalw_hsr"),
            ("Federal money pulled, July 2025", "$4B", "ktvu_hsr"),
        ],
        "redact": ("Date trains run San Francisco to L.A.", "NONE GIVEN"),
        "happened": [
            "In 2008 California voters approved bonds for a high-speed line from San Francisco to Los Angeles, with a price tag of about $33 billion and a 2020 finish.",
            "The Authority's 2026 business plan puts the full line at $126 billion to $231 billion. The first segment, 171 miles in the Central Valley, is set to carry passengers in 2033, and nearly $87 billion still has to be found.",
        ],
        "missed": [
            "In July 2025 the Federal Railroad Administration pulled $4 billion in federal funding. The state has since dropped its lawsuit to get it back.",
        ],
        "sure": "The Authority's own estimates, as reported. The 2008 price and today's aren't in the same year's dollars, so part of the growth is inflation. Cost overruns are not fraud.",
        "sources": ["ktvu_hsr", "kalw_hsr", "ra_hsr"],
    },
    {
        "slug": "honolulu-rail",
        "level": "local", "place": "Honolulu Authority for Rapid Transportation", "tier": "overrun", "type": "soft",
        "fig": "$10.1", "scale": "billion, double the plan",
        "title": "Honolulu's rail line: twice the cost, a mile shorter",
        "dek": "Honolulu's elevated rail line was estimated at about $5 billion when construction began in 2011. Its official budget is now $10.079 billion, the line stops about a mile short of Ala Moana Center, and full service is targeted for 2031.",
        "sort": 10.079e9,
        "receipt": [
            ("Estimate when construction began, 2011", "About $5B", "civilbeat_hart"),
            ("Official budget now", "$10.079B", "civilbeat_hart"),
            ("Risk analysis, with financing", "Up to $10.19B", "civilbeat_hart"),
            ("Length", "18.9 miles, elevated", "civilbeat_hart"),
            ("Cut from the route", "About 1 mile (to Ala Moana)", "civilbeat_hart"),
            ("Full service target", "2031", "civilbeat_hart"),
        ],
        "redact": ("Final cost", "NOT KNOWN YET"),
        "happened": [
            "Construction on Honolulu's rail line began in 2011 with an estimate of about $5 billion.",
            "The official budget is now $10.079 billion, and the line was cut short: it ends in Kakaʻako instead of a mile farther at Ala Moana Center. A recent risk analysis says the total with financing could reach $10.19 billion.",
        ],
        "missed": [
            "A consultant for the Federal Transit Administration is reviewing the project's cost and schedule.",
        ],
        "sure": "The rail authority's official budget and its own risk analysis, as reported by Civil Beat in August 2026. Overruns are not fraud.",
        "sources": ["civilbeat_hart"],
    },
    {
        "slug": "medicare-generic-drug-prices",
        "level": "federal", "place": "Medicare Part D", "tier": "estimated", "type": "soft",
        "fig": "$3.6", "scale": "billion in one year",
        "title": "Medicare paid far more for cheap generics than an online pharmacy charges",
        "dek": "A study in the Annals of Internal Medicine estimated Medicare could have saved $3.6 billion in a single year by paying Mark Cuban Cost Plus Drug Company's prices for 77 generic drugs.",
        "sort": 3.6e9,
        "receipt": [
            ("Estimated savings, one year", "$3.6B", "medecon_cuban"),
            ("Generic drugs compared", "89", "medecon_cuban"),
            ("Drugs where Medicare paid more", "77", "medecon_cuban"),
            ("Esomeprazole, 90 pills: Medicare", "$160", "medecon_cuban"),
            ("Esomeprazole, 90 pills: Cost Plus", "$17", "medecon_cuban"),
            ("Savings on esomeprazole alone", "$293M of $327M spent", "medecon_cuban"),
        ],
        "redact": ("Who kept the difference", "NOT IN THE STUDY"),
        "happened": [
            "Researchers compared what Medicare's drug plans paid for 89 generic drugs, using 2020 data, with the prices posted by Mark Cuban Cost Plus Drug Company, which sells at its cost plus a fixed markup.",
            "Medicare paid more for 77 of them. Paying the posted prices would have saved an estimated $3.6 billion in one year. For one heartburn drug, Medicare paid $160 for 90 pills; Cost Plus charged $17.",
        ],
        "missed": [
            "Medicare doesn't buy drugs directly. Private drug plans negotiate the prices, and Medicare pays the bills.",
        ],
        "sure": "A peer-reviewed estimate (Lalani et al., Annals of Internal Medicine, June 2022) using 2020 Medicare data and 2022 prices. Overpaying isn't fraud; it's the price problem the RECEIPTS Act is about.",
        "sources": ["medecon_cuban"],
    },
]

for c in NEW:
    TYPE[c["slug"]] = c["type"]
CASES.extend(NEW)

# ------------------------------------------------------------------ update the running total with the official dataset
for c in CASES:
    if c["slug"] == "improper-payments-since-2003":
        c["fig"] = f"${CUM/1e12:.2f}".rstrip("0")
        c["scale"] = "trillion since 2004"
        c["sort"] = CUM
        c["dek"] = f"Federal agencies have reported ${CUM/1e12:.2f} trillion in improper and unverifiable payments since fiscal {FIRST_YEAR}, by our count of the government's own dataset. Fiscal 2025 alone added {_bn(FY25/1e6)}."
        c["receipt"] = [
            (f"Improper and unverifiable payments, FY{FIRST_YEAR}–FY2025", f"${CUM/1e12:.2f} trillion", "pa_data"),
            (f"Of that, FY{FIRST_YEAR}–FY2024 (GAO: ≈$2.8T)", f"${CUM24/1e12:.2f} trillion", "pa_data"),
            ("FY2025 alone", _bn(FY25/1e6), "pa_data"),
            ("Programs with error rates over 10%, FY2025", str(OVER10), "pa_data"),
            ("Overpayments flagged for recovery, FY2025", _bn(REC25["identified_m"]), "pa_data"),
            ("Actually recovered, FY2025", _bn(REC25["recovered_m"]), "pa_data"),
            ("TANF's error rate", "Never reported", "gao_ip_cum"),
        ]
        c["redact"] = ("Programs not measured at all", "NOT COUNTED")
        c["happened"] = [
            "Since the early 2000s, agencies have had to estimate how much they pay out wrongly or without the records to prove it. The government publishes every program's numbers in one dataset on PaymentAccuracy.gov.",
            f"We added them up. From fiscal {FIRST_YEAR} through 2025 the total is ${CUM/1e12:.2f} trillion. Through 2024 it's ${CUM24/1e12:.2f} trillion, matching GAO's published figure of about $2.8 trillion.",
        ]
        c["missed"] = [
            "The total only counts programs that report. Temporary Assistance for Needy Families has never been included; HHS says it lacks the authority to get the data.",
            f"In fiscal 2025, agencies flagged {_bn(REC25['identified_m'])} in overpayments to claw back and recovered {_bn(REC25['recovered_m'])}.",
        ]
        c["sure"] = "These are the government's own estimates; the totals are FraudBad's sums of the official dataset. Improper payments include errors and missing paperwork as well as fraud."
        c["sources"] = ["pa_data", "gao_ip_cum", "gao_ip"]

# Home/soft tiles: replace the GAO-through-2024 tile with the dataset total, add the new ones.
for i, t in enumerate(SOFT_BIG):
    if t[2] == "improper-payments-since-2003":
        SOFT_BIG[i] = (f"${CUM/1e12:.1f}T", f"paid wrong or without proof since {FIRST_YEAR}", "improper-payments-since-2003", "pa_data")
SOFT_BIG.insert(3, ("$217B", "owed to the government, overdue, and not collected", "federal-debt-never-collected", "treas_debt24"))
SOFT_BIG.insert(4, (f"${RC_FAIL/1e9:,.0f}B", "paid wrong in one year when the data to stop it existed", "data-existed-nobody-checked", "pa_data"))
SOFT_BIG.append((_bn(R25["sep"]/1e6, 0), "in contracts signed in the last month of fiscal 2025", "september-spending-rush", "usas_month"))

# Signals: point each at its new examples.
_ex = {"01": ["data-existed-nobody-checked", "shuttered-venue-grants", "hud-rental-assistance-unverified"],
       "02": ["medicare-generic-drug-prices"],
       "03": ["sentinel-icbm-overrun", "california-high-speed-rail", "honolulu-rail"],
       "05": ["federal-debt-never-collected", "social-security-overpayments"],
       "07": ["september-spending-rush"]}
for i, s in enumerate(SIGNALS):
    num, name, what, where, measure, ex = s
    if num in _ex:
        SIGNALS[i] = (num, name, what, where, measure, ex + [x for x in _ex[num] if x not in ex])
    if num == "05":
        SIGNALS[i] = (num, name, what, "IRS tax gap projections; Treasury's yearly report on delinquent non-tax debt; uncollected overpayment balances in agency financial reports.", measure, SIGNALS[i][5])
    if num == "07":
        SIGNALS[i] = (num, name, what, "Contract obligations by fiscal month on USAspending.gov. Research found agencies spend 4.9 times a normal week's amount in the last week of the fiscal year, and last-week IT projects were 2 to 6 times more likely to be rated lower quality.",
                      "September's share of the year's contract obligations vs. 1/12 (8.3%).", SIGNALS[i][5])
