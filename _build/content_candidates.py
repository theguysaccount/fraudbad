# -*- coding: utf-8 -*-
"""Candidate cases found in the weekly run of Nov 16, 2026 (search window Nov 9-16, 2026).
NOT imported anywhere. Nothing here is live until Jack says "publish N".
Every figure below was read on the cited page itself, not from a search snippet."""
from content import S

S.update({
    "doj_sadc_2026": ("Social adult day care program director pleads guilty in $127M Medicare and Medicaid fraud scheme", "U.S. Department of Justice", "Nov 10, 2026", "https://www.justice.gov/opa/pr/social-adult-day-care-program-director-pleads-guilty-127m-medicare-and-medicaid-fraud-scheme"),
    "gao_sba_ip": ("GAO-27-107701: Small Business Administration: opportunities exist to improve improper payment estimation and recovery processes", "U.S. Government Accountability Office", "Nov 9, 2026", "https://www.gao.gov/products/gao-27-107701"),
    "gao_f35_parts": ("GAO-27-108713: F-35 program: DOD needs to strengthen oversight of tens of billions of dollars in parts", "U.S. Government Accountability Office", "Nov 9, 2026", "https://files.gao.gov/reports/GAO-27-108713/index.html"),
})

CANDIDATES = [
    # 1 ------------------------------------------------------------------
    {
        "slug": "f35-spare-parts",
        "level": "federal", "place": "Department of Defense, F-35 program", "tier": "unauditable", "type": "soft",
        "fig": "$31", "scale": "billion in parts it can't fully track",
        "title": "$31 billion in F-35 parts the Pentagon can't fully account for",
        "dek": "The government owns about 26 million F-35 spare parts worth about $31 billion, spread across more than 700 sites. GAO says the records still can't show what's there.",
        "sort": 31e9,
        "receipt": [
            ("F-35 parts the government owns", "≈26 million", "gao_f35_parts"),
            ("Their value (March 2026)", "≈$31B", "gao_f35_parts"),
            ("Sites holding them", "700+", "gao_f35_parts"),
            ("Parts one contractor lost, May 2018–Oct 2022", "1M+ parts, $85M+", "gao_f35_parts"),
            ("Losses submitted for review so far", "≈$28M", "gao_f35_parts"),
            ("Contractor held liable for", "≈$6M", "gao_f35_parts"),
            ("Spent on parts counts since FY2020", "$17M+", "gao_f35_parts"),
            ("Parts records with a serial number (Dec 2025)", "29%", "gao_f35_parts"),
            ("Watchdog fixes still open (Aug 2026)", "26 of 34", "gao_f35_parts"),
        ],
        "redact": ("Where the missing parts went", "UNKNOWN"),
        "happened": [
            "The F-35 program buys spare parts that the government owns but contractors hold, at more than 700 contractor and government sites worldwide.",
            "GAO reported on Nov 9, 2026 that the program's records for about 26 million parts, worth about $31 billion, still don't reliably show what exists and where. Only 29% of parts records in December 2025 had a serial number, and almost 6% listed a cost of one cent or less.",
        ],
        "missed": [
            "In 2023 GAO found one prime contractor had lost over 1 million parts worth over $85 million. As of March 2026 about $28 million in losses had been submitted for review, and the contractor was held liable for about $6 million.",
            "The program has spent at least $17 million on physical counts since fiscal 2020. As of August 2026, 26 of 34 GAO and Pentagon inspector general recommendations were still open.",
        ],
        "sure": "GAO's own findings. This is money the Pentagon can't account for, not proven theft. Law requires a clean Pentagon audit by Dec 31, 2028.",
        "sources": ["gao_f35_parts"],
    },
    # 2 ------------------------------------------------------------------
    {
        "slug": "sba-overpayments-not-recovered",
        "level": "federal", "place": "Small Business Administration", "tier": "uncollected", "type": "soft",
        "fig": "$616", "scale": "million overpaid, under 1% recovered",
        "title": "SBA found $616 million in overpayments and got back less than 1%",
        "dek": "In fiscal 2025 the Small Business Administration identified $616.2 million in overpayments. It recovered less than 1% of it. Across the government, agencies recovered 62%.",
        "sort": 616.2e6,
        "receipt": [
            ("Overpayments SBA identified, FY2025", "$616.2M", "gao_sba_ip"),
            ("Share SBA recovered", "Less than 1%", "gao_sba_ip"),
            ("Share recovered government-wide", "62%", "gao_sba_ip"),
            ("Improper payments estimated for 2025 in the programs reviewed", "≈$2B", "gao_sba_ip"),
            ("Years since SBA last rethought recovery audits (7(a) / standard EIDL)", "10 / 15", "gao_sba_ip"),
            ("GAO recommendations", "4 (SBA disagreed with 2)", "gao_sba_ip"),
        ],
        "redact": ("Borrowers overpaid, by name", "NOT PUBLISHED"),
        "happened": [
            "GAO looked at how SBA measures and recovers improper payments in its pandemic loan programs (PPP and COVID-19 EIDL) and its regular 7(a) and disaster loans. It estimated about $2 billion in improper payments for 2025 across those programs.",
            "SBA identified $616.2 million in overpayments in fiscal 2025 and recovered less than 1% of it, against 62% government-wide.",
        ],
        "missed": [
            "SBA doesn't run recovery audits for 7(a) or standard EIDL loans and hadn't revisited those decisions in 10 and 15 years.",
            "GAO said SBA didn't check whether its PPP and COVID-19 EIDL estimates reflected known fraud risks, and didn't document the basis for key estimating decisions. SBA disagreed with two of GAO's four recommendations.",
        ],
        "sure": "GAO's findings from SBA's own figures. Overpayments include errors, not only fraud.",
        "sources": ["gao_sba_ip"],
    },
    # 3 ------------------------------------------------------------------
    {
        "slug": "queens-adult-day-care-fraud",
        "level": "state", "place": "Flushing, New York", "tier": "confirmed",
        "fig": "$127", "scale": "million",
        "title": "Adult day care billed Medicaid for people who were in the hospital",
        "dek": "A program director at two Flushing, New York adult day care centers pleaded guilty in a Medicare and Medicaid fraud that prosecutors put at about $127 million over about ten years.",
        "sort": 127e6,
        "receipt": [
            ("Fraud on Medicare and NY Medicaid, per prosecutors", "≈$127M", "doj_sadc_2026"),
            ("How long it ran", "≈10 years", "doj_sadc_2026"),
            ("Cash found in a search of one center", "$100K+", "doj_sadc_2026"),
            ("Seized from bank accounts", "≈$900K", "doj_sadc_2026"),
            ("Plea", "Guilty, Nov 9, 2026", "doj_sadc_2026"),
            ("Sentencing", "Mar 2, 2027 (max 30 years)", "doj_sadc_2026"),
        ],
        "redact": ("Recovered so far", "≈$1M SEIZED"),
        "happened": [
            "Daniel Lee, a program director at Happy Life Inc. and Royal Adult Day Care Center in Flushing, Queens, pleaded guilty on Nov 9, 2026 to conspiracy to commit health care fraud and conspiracy to commit money laundering.",
            "Prosecutors say the centers paid Medicaid recipients cash kickbacks to enroll and billed Medicaid for services never given, including days when the recipients were in the hospital. A related pharmacy paid kickbacks and billed for drugs that weren't medically necessary.",
        ],
        "missed": [
            "The billing ran for about ten years before charges. The release does not say how much Medicare and Medicaid paid out before it was caught.",
        ],
        "sure": "A guilty plea. The $127 million is the scheme total as the Justice Department describes it, not an amount the court has found against this defendant. Sentencing is set for March 2, 2027.",
        "sources": ["doj_sadc_2026"],
    },
]
