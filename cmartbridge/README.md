# CmartBridge Rwanda 🇰🇷→🇷🇼

AI-powered sourcing, logistics and commerce bridge between Rwanda and Asian manufacturers — starting with South Korea. Founder buys in Korea; a trusted operator receives, clears (RRA) and delivers in Kigali.

**Phase 1 (this repo):** started as WhatsApp + Instagram ordering with a one-page request form. Pulled forward from the original Phase 2 plan: the site now also has real product pages, a cart, and checkout with **instant MTN MoMo payment** — Airtel Money and bank transfer stay on the original manual WhatsApp-confirmation flow (no API access for those yet). Still no accounts, no order-history dashboard — fulfillment is still 5 manual WhatsApp status updates per order.

## The model (locked decisions)

- **Revenue:** 30% commission on product price. Shipping, customs and VAT passed through at cost.
- **One all-in "delivered to your door" price** — breakdown on request, no hidden fees, ever.
- **Payments:** MTN MoMo / Airtel Money first, bank transfer second. 100% upfront — money in before money out, always.
- **Loss policy:** every shipment tracked; lost or damaged = reship or full refund. ~5% buffer covers losses + KRW→RWF moves.

## The site

React + Vite, React Router for navigation: home page (hero → why us → how it works → 20-item starter catalog with live door prices → landed-cost estimator → WhatsApp request form → prohibited-items list → T&Cs) plus `/product/:id`, `/cart`, `/checkout`, `/order-confirmation`. Full EN / Kinyarwanda toggle.

```bash
cd cmartbridge
npm install
cp .env.example .env   # then fill in your MTN MoMo credentials — see below
npm run dev             # runs the Vite dev server AND the API together
npm run build            # production build (dist/)
npm start                 # production: one process serves the built site + API
npm run catalog:print   # regenerate the catalog price table for docs
```

Door prices everywhere come from **one** pricing engine: `src/lib/pricing.js`, plus `src/lib/cartTotals.js` for cart/checkout totals. Rates (duty, VAT, shipping, buffer) live in `CONFIG` — placeholders flagged in-code must be verified (RRA, Korea Post) before launch. The KRW→RWF **exchange rate is fetched live** (client-side via `src/hooks/useFxRate.js`, server-side via `server/fx.js`, both hitting the free `open.er-api.com` API); `CONFIG.krwToRwf` is only the offline fallback used if that fetch fails.

**Before going live:** set the real WhatsApp number / Instagram / email in `src/data/site.js`, and have a native speaker review the Kinyarwanda in `src/i18n.js` and the T&Cs.

### Cart & checkout (MTN MoMo)

The 20-item catalog can be added to a cart (browser-only, `localStorage`, no database) and checked out two ways:

- **MTN MoMo** — instant. `POST /api/momo/pay` (`server/routes.js`) never trusts the amount the browser sends: it re-validates every cart line against `CATALOG` and refetches the FX rate server-side, then charges the total *it* computed. Needs real credentials in `.env` (copy `.env.example`) — get a free sandbox account at [momodeveloper.mtn.com](https://momodeveloper.mtn.com). Sandbox only accepts `MOMO_CURRENCY=EUR` for test payments; switch to `RWF` once `MOMO_TARGET_ENVIRONMENT=mtnrwanda` (production).
- **Airtel Money / bank transfer** — unchanged from the original flow: builds a WhatsApp message (now with the full cart) and opens it for manual confirmation.

**Operational note:** because there's no order database, a MoMo payment is only ever surfaced to you via (a) the customer tapping "Send my order to CmartBridge on WhatsApp" on the confirmation screen, or (b) you checking the MTN MoMo merchant dashboard directly. Check that dashboard on a regular cadence — don't rely solely on (a).

## Docs (Phase 1 operating kit)

| Doc | What it is |
|-----|------------|
| [`docs/90-day-launch-plan.md`](docs/90-day-launch-plan.md) | Week-by-week plan to 100 orders, with the standing weekly rhythm |
| [`docs/landed-cost-pricing-template.md`](docs/landed-cost-pricing-template.md) + [`.xlsx`](docs/landed-cost-pricing-template.xlsx) | Pricing model, spreadsheet formulas, working workbook |
| [`docs/whatsapp-message-templates.md`](docs/whatsapp-message-templates.md) | The 5 status updates + quote/decline/delay, EN + RW |
| [`docs/terms-and-conditions.md`](docs/terms-and-conditions.md) | Draft T&Cs, English + Kinyarwanda |
| [`docs/starter-catalog.md`](docs/starter-catalog.md) | 20 starter products with computed door prices |

## Still ahead (gated on ~100 successful orders)

Accounts / order history · Airtel Money API integration (once available) · AI demand forecasting trained on the order log · China (1688) and Japan sourcing · then insurance, B2B bulk, subscriptions, beyond Kigali.
