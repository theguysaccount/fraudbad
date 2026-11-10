# america.co changes for FraudBad (plan items 0.4–0.7)

**Why:** fraudbad.com sends every reader to `https://america.co/receipts-act`. Today a signature can't be traced to the page that earned it, the count is invisible, and signing ends at a thank-you. These four changes close that loop.

**Where:** the live code is `FlicLabs/america-co` (Vercel project `america-co`, team Persist). Confirm you're on the branch that serves `/receipts-act` today: it contains `data-newsletter-form` in the page and `/newsletter.js`, and posts to `/api/newsletter`. `persist-ventures/america-co` is an old copy (last commit Aug 15, 2026) — don't deploy from it.

**What fraudbad.com already sends** (live since Nov 10, 2026):

```
https://america.co/receipts-act?ref=fraudbad-a&case=<page>&pos=<button>#sign
```

- `ref` — `fraudbad-a` or `fraudbad-b` (which wording version the reader saw; plain `fraudbad` with scripts off)
- `case` — the page slug, e.g. `feeding-our-future`, `ledger`, `state-mn`, `program-hhs-medicaid`
- `pos` — `nav`, `band`, `footer`, `inline` or `bar`

## 0.4 Record who sent each signer

1. In `newsletter.js`, before the POST, read `ref`, `case` and `pos` from `location.search`. Keep each only if it matches `/^[a-z0-9-]{1,64}$/`. Send them as `ref`, `refCase`, `refPos`.
2. In `/api/newsletter`, validate with the same pattern (drop anything else, never reject the signup over it) and save them on the signup row: three new nullable text columns `ref`, `ref_case`, `ref_pos`.
3. Add one line to the privacy page: "If you arrive from a link that names where it came from (like fraudbad.com), we save that name with your signup. We don't follow you across sites."

**Done when:** a test signup from `/receipts-act?ref=fraudbad&case=test&pos=band#sign` shows `fraudbad / test / band` on its row.

## 0.5 Show the count

1. `GET /api/receipts-act/count` → `{"count": <n or null>, "updatedAt": "<iso>"}`. Count distinct consenting emails with `purpose = 'receipts-act'`. Return `null` below 100. Header `Cache-Control: public, s-maxage=300`.
2. Allow fraudbad to read it: `Access-Control-Allow-Origin: https://fraudbad.com`.
3. Print it beside the form: "**N** people have signed." Hide the line when the count is `null`.

**Done when:** the endpoint returns the true number and the page shows it.

## 0.6 Add the share step

1. On a successful signup, give the signer a code: the first 8 characters of a hash of their `requestId`. Store it as `share_code`.
2. Replace the thank-you's dead end with three buttons, each using `https://america.co/receipts-act?ref=s-<code>#sign`:
   - **Copy my link**
   - **Post on X**: `https://x.com/intent/post?text=<text>&url=<link>`
   - **Text a friend**: `sms:?&body=<text> <link>`
   Text: "I signed for receipts on public spending. Add your name:"
3. A signup arriving with `ref=s-<code>` is credited to that signer. `GET /api/receipts-act/tally?code=<code>` returns how many.

**Done when:** a second signup through a personal link raises that signer's tally by one.

## 0.7 Let fraudbad.com post the form directly

1. `/api/newsletter` answers the preflight: `OPTIONS` → 204 with `Access-Control-Allow-Origin: https://fraudbad.com`, `Access-Control-Allow-Methods: POST, OPTIONS`, `Access-Control-Allow-Headers: content-type`, `Access-Control-Max-Age: 86400`. Add the same `Allow-Origin` header to the POST response. No other origins.
2. Nothing else changes: same fields, same consent text, same honeypot, same rate limit.

Today the endpoint answers the preflight with `405`. After this change, fraudbad.com will add the email field, the consent box and the privacy link to its red band, posting to `https://america.co/api/newsletter` with `source=fraudbad.com/<page>`, `purpose=receipts-act` and the same three tags.

**Done when:** a signup made on a fraudbad.com case page lands with `ref=fraudbad` and that case's slug, without leaving the page.

## 2.3 "Endorsed by" block (ship hidden, turn on at the first yes)

1. Add a block under the form on `/receipts-act`: heading "Endorsed by", then one row per group: logo (max 40 px tall, grayscale), group name, a one-line quote, a link to their statement.
2. Drive it from a small list in the code (`endorsers = []`). When the list is empty, render nothing — no heading, no empty state.
3. Add a group only with a written yes from someone at that group who can speak for it, and keep that message.

**Done when:** adding one entry to the list shows the block; an empty list shows nothing.

## After all of these

Tell the FraudBad plan doc ("FraudBad: the rest of the plan") so items 0.4–0.7 and the 2.3 block can be ticked, and run one test signature end to end.
