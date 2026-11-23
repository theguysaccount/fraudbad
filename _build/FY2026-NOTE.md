# FY2026 improper-payment file is out — what changed from FY2025

Source: https://paymentaccuracy.gov/assets/files/FY2026_Dataset.xlsx (posted Nov 16, 2026; pulled Nov 23, 2026).
All figures below are FraudBad sums of that file, built by `make_ledger.py 2026` into `data/ledger_fy2026.json`.

- Paid wrong or without proof, FY2026: $197.5B across 66 programs (FY2025: $185.8B across 64). Up $11.6B.
- Running total since FY2004: $3.18T (through FY2025: $2.98T).
- Biggest: Medicaid $46.8B (7.1%, up from 6.1%); Medicare fee-for-service $34.0B (7.3%, up from 6.6%); Medicare Advantage $23.9B (5.7%, down from 6.1%); EITC $22.7B (32.2%); SNAP $10.1B (10.6%).
- "Failure to access data" — data existed and nobody checked: $138.3B of the $197.5B.
- Overpayments flagged for recovery, FY2026: $44.5B; recovered: $29.1B.
- Payment-integrity law, FY2025 ratings: 13 of 58 rated agencies non-compliant (FY2024: 15 of 63).

## Why this isn't live yet
- The FY2026 file renames many programs and agencies (e.g. "TREASURY", "FTA Capital Investment Grants (Section 5309)"). Switching would remove 10 existing /program/ pages (incl. the EITC and FTA Capital Investment Grants pages linked from cases) and add 13 new ones. Those need redirects.
- Dozens of hand-written lines in build.py, content_more.py and pages_more.py say "FY2025", "64 programs", "matches GAO's $186B", etc., plus the SVOG, HUD rental-assistance and improper-payments cases. They need rewording to FY2026, and GAO has not yet published an FY2026 total to compare against.
