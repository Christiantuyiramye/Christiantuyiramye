# CmartBridge Rwanda — 90-Day Launch Plan (Phase 1)

**Goal:** 100 successful orders in Kigali in 90 days, every one logged, zero money lost.
**Team:** Founder + cousin (Korea side) · trusted operator in Kigali — *(NAME REQUIRED — do not launch without this person signed up)* — (Rwanda side).
**Cash-flow rule (non-negotiable):** money in before money out. We never buy before the customer's payment has cleared.

---

## Weeks 1–2 — Legal, banking & rails

- [ ] Register the business with RDB (online, ~1 day, low cost) and get the TIN. You are becoming an importer of record — keep **every** import receipt from day one.
- [ ] Open MTN MoMo **business** account and Airtel Money account; test receiving + withdrawing. Bank account as backup rail.
- [ ] Kigali operator: agree role in writing — receive shipments, clear with RRA, last-mile delivery / pickup point, and their compensation.
- [ ] Verify with RRA: duty rate per Phase 1 category (EAC CET 0–25%), VAT 18% treatment, de minimis thresholds, and what paperwork EMS parcels need. Update `pricing.js` and the pricing spreadsheet with real rates.
- [ ] Verify with Korea Post: current EMS service to Rwanda, rates, weight limits, prohibited list. Get a courier quote (e.g. DHL) as fallback. Update the shipping rate in the pricing template.
- [ ] Set up WhatsApp Business (catalog, greeting, away messages, labels: NEW / QUOTED / PAID / PURCHASED / SHIPPED / ARRIVED / DELIVERED / DECLINED).
- [ ] Create the order log spreadsheet (this is the Phase 2 AI training data): date, customer, channel, item, link, category, KRW cost, weight, quote, paid?, purchased date, shipped date, tracking #, arrived, delivered, margin, notes — **plus a "declined requests" tab** logging every "sorry, we can't get that" with the reason.

## Weeks 3–4 — Price validation & content

- [ ] **Pre-launch price test:** fully cost out the 10 fastest-moving sample products (product + shipping + duty + VAT + 30% + 5% buffer) with the pricing template.
- [ ] Compare each against (a) Kigali market price (walk Kigali City Market / Chic Mall, screenshot Jumia/Kikuu listings) and (b) AliExpress landed cost. If a category fails, adjust its commission — decide per category, keep the all-in price honest.
- [ ] Lock the starter catalog of 20 items (see `starter-catalog.md`), with photos taken in Korea.
- [ ] Set up Instagram business profile; publish the catalog with door prices in RWF.
- [ ] Deploy the one-page site (this repo: `cmartbridge/`) with the real WhatsApp number; test the request form end-to-end on a phone.
- [ ] Finalize T&Cs (EN + Kinyarwanda, see `terms-and-conditions.md`) — have a native Kinyarwanda speaker review. Link them in WhatsApp and Instagram bios.
- [ ] Load the 5 WhatsApp status templates (see `whatsapp-message-templates.md`) as Quick Replies.

## Week 5 — Friends & family pilot (orders 1–10)

- [ ] Take 5–10 orders from people you know. Full process, no shortcuts: quote → MoMo payment → buy → photo → EMS → clear → deliver.
- [ ] Send all 5 status updates for every order, even to your cousin's friend.
- [ ] Time every stage (payment→purchase, purchase→ship, ship→arrive, arrive→deliver). This is your first real 2–4 week evidence.
- [ ] First consolidated EMS batch: weigh it, record the actual per-kg cost, compare to the 11 RWF/g assumption in the template. Correct it.

## Week 6 — First customs reality check

- [ ] Kigali operator clears the first batch with RRA. Record actual duty + VAT charged per category vs. the estimates. **Fix the estimator rates immediately** — wrong estimates eat the 30% alive.
- [ ] Deliver pilot orders; collect a WhatsApp testimonial + photo from each happy customer (ask permission to post).
- [ ] Post-mortem: what broke? Fix the process, not the symptom.

## Weeks 7–8 — Soft public launch (orders 11–30)

- [ ] Announce publicly: Instagram + personal networks + 2–3 Kigali WhatsApp/Telegram groups (K-pop fan groups, campus groups, ladies' market groups).
- [ ] Push the 3 proven winners from the pilot as hero products.
- [ ] Weekly rhythm starts: **Mon** close orders / **Tue** buy + photo customers / **Wed** pack + EMS / then track → clear → deliver.
- [ ] Refresh the KRW→RWF rate in the template (do this every Monday, BNR reference rate).
- [ ] Track weekly: orders, revenue, actual margin per order, declined requests, delivery days.

## Weeks 9–10 — Tighten the loop (orders 31–55)

- [ ] Review the declined-requests log — is there a category we *can* legally add? Add it to the catalog if the numbers work.
- [ ] Negotiate Dongdaemun wholesale pricing on the 5 best sellers (better margin at same door price).
- [ ] Trial a pickup point (shop/kiosk deal) if door delivery is eating time.
- [ ] Referral push: "refer a friend, get 2,000 RWF off your next order" (cheapest acquisition in Kigali).
- [ ] Check buffer performance: has the 5% covered FX moves + any loss? Adjust if not.

## Weeks 11–12 — Scale the weekly batch (orders 56–85)

- [ ] Target 15–20 orders/week; consider two EMS batches per week if weight caps are hit.
- [ ] Systematize photos: consistent background + logo card in every purchase photo (this *is* the brand).
- [ ] Collect and post testimonials weekly; pin the "how it works — 5 updates" explainer.
- [ ] Dry-run a loss claim: know the EMS claim process with Korea Post *before* you need it.
- [ ] Start the Phase 2 data review: top categories, repeat customers, average order value, request→paid conversion.

## Week 13 — 100-order review & Phase 2 gate

- [ ] Hit / assess the 100-order mark. For each category: actual margin after all costs vs. the 30% target.
- [ ] Clean the order log — this is the AI forecasting training set. Every row complete.
- [ ] Write the Phase 1 report: unit economics, delivery-time distribution, loss rate, top decline reasons, cash position.
- [ ] **Phase 2 go/no-go:** only if ~100 successful orders, margin holds, and the weekly rhythm runs without heroics. Then: real web platform, AI demand forecasting on the log, China (1688) & Japan sourcing.

---

## Standing weekly rhythm (from week 7)

| Day | Korea side (founder + cousin) | Kigali side (operator) |
|-----|-------------------------------|------------------------|
| Mon | Close weekly orders, confirm payments, refresh FX rate | Push catalog in groups, collect requests |
| Tue | Buy everything, photograph, send "purchased" updates | — |
| Wed | Pack, consolidate, ship EMS, send tracking numbers | — |
| Thu–Fri | Log everything, quote new requests | Chase last week's batch: RRA clearance, deliveries |
| Sat | Content: photos, reels, testimonials | Deliveries / pickup point hours |
| Sun | Off. Burnout kills 90-day plans. | Off. |

## Numbers to watch every single week

1. Orders taken / orders delivered
2. Actual margin per order (target: commission survives after real duty + shipping)
3. Average payment→door days (promise: 14–28)
4. Declined requests + reasons (Phase 2 gold)
5. Cash position (must never require buying before payment — if it does, stop and fix)
