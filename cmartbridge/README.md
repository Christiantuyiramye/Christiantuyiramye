# CmartBridge Rwanda 🇰🇷→🇷🇼

AI-powered sourcing, logistics and commerce bridge between Rwanda and Asian manufacturers — starting with South Korea. Founder buys in Korea; a trusted operator receives, clears (RRA) and delivers in Kigali.

**Phase 1 (this repo):** WhatsApp + Instagram ordering, and this one-page site with a request form. Deliberately *not* a full e-commerce platform — that's Phase 2, after ~100 successful orders.

## The model (locked decisions)

- **Revenue:** 30% commission on product price. Shipping, customs and VAT passed through at cost.
- **One all-in "delivered to your door" price** — breakdown on request, no hidden fees, ever.
- **Payments:** MTN MoMo / Airtel Money first, bank transfer second. 100% upfront — money in before money out, always.
- **Loss policy:** every shipment tracked; lost or damaged = reship or full refund. ~5% buffer covers losses + KRW→RWF moves.

## The site

React + Vite one-pager: hero → why us → how it works (the 5 WhatsApp status points) → 20-item starter catalog with live door prices → landed-cost estimator with on-request breakdown → WhatsApp request form → prohibited-items list → T&Cs. Full EN / Kinyarwanda toggle.

```bash
cd cmartbridge
npm install
npm run dev        # local dev server
npm run build      # production build (dist/)
npm run catalog:print   # regenerate the catalog price table for docs
```

Door prices everywhere come from **one** pricing engine: `src/lib/pricing.js`. Rates (FX, duty, VAT, shipping, buffer) live in its `CONFIG` — placeholders flagged in-code must be verified (BNR, RRA, Korea Post) before launch.

**Before going live:** set the real WhatsApp number / Instagram / email in `src/data/site.js`, and have a native speaker review the Kinyarwanda in `src/i18n.js` and the T&Cs.

## Docs (Phase 1 operating kit)

| Doc | What it is |
|-----|------------|
| [`docs/90-day-launch-plan.md`](docs/90-day-launch-plan.md) | Week-by-week plan to 100 orders, with the standing weekly rhythm |
| [`docs/landed-cost-pricing-template.md`](docs/landed-cost-pricing-template.md) + [`.xlsx`](docs/landed-cost-pricing-template.xlsx) | Pricing model, spreadsheet formulas, working workbook |
| [`docs/whatsapp-message-templates.md`](docs/whatsapp-message-templates.md) | The 5 status updates + quote/decline/delay, EN + RW |
| [`docs/terms-and-conditions.md`](docs/terms-and-conditions.md) | Draft T&Cs, English + Kinyarwanda |
| [`docs/starter-catalog.md`](docs/starter-catalog.md) | 20 starter products with computed door prices |

## Phase 2 (gated on ~100 successful orders)

Real web platform with accounts · AI demand forecasting trained on the Phase 1 order log · China (1688) and Japan sourcing · then insurance, B2B bulk, subscriptions, beyond Kigali.
