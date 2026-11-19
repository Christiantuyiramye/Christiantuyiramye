# CmartBridge Rwanda — Landed-Cost Pricing Template

**The working file is [`landed-cost-pricing-template.xlsx`](./landed-cost-pricing-template.xlsx)** — two sheets (`Assumptions`, `Pricing`), live formulas, pre-loaded with the 20 starter-catalog items. It opens in Excel, Google Sheets and LibreOffice. This page documents the model so you can rebuild or audit it anywhere.

The same formulas power the website estimator (`src/lib/pricing.js`) — change a rate in one place, change it in both.

## The model

```
door price = product + commission + shipping + duty + VAT + buffer   → rounded UP to 500 RWF
```

| Component | Formula | Rule |
|-----------|---------|------|
| Product (RWF) | `KRW price × FX rate` | FX refreshed **weekly** (BNR reference rate) |
| Commission | `product × 30%` | our only revenue — on product price, never on shipping/taxes |
| Shipping | `max(weight_g × rate_per_g, minimum)` | passed through **at cost** from the consolidated EMS batch |
| Duty | `(product + shipping) × category duty rate` | EAC CET 0–25% by category — **verify with RRA** |
| VAT | `(product + shipping + duty) × 18%` | passed through at cost |
| Buffer | `(product + shipping) × 5%` | covers KRW→RWF swings + lost/damaged reships |

Quoted to the customer as **one all-in door price**; breakdown available on request. Wrong duty estimates eat the 30% alive — check actual RRA charges against the estimates weekly and correct the rates.

## Spreadsheet layout & formulas

**Sheet `Assumptions`** (all inputs, yellow cells):

| Cell | Value | Note |
|------|-------|------|
| B3 | 1.05 | KRW→RWF — refresh every Monday |
| B4 | 30% | commission |
| B5 | 5% | FX & loss buffer |
| B6 | 18% | VAT |
| B7 | 11 | shipping RWF per gram — verify against actual EMS batch cost |
| B8 | 600 | minimum shipping per item (RWF) |
| B9 | 500 | round door price up to nearest |
| A12:B16 | category → duty | K-Beauty 25% · Phone acc. 10% · Fashion 25% · K-pop 25% · Stationery 25% — **placeholders, verify with RRA** |

**Sheet `Pricing`** — inputs per row: `A` item, `B` category (must match the duty table), `C` Korea price KRW, `D` weight g. Formulas (row 2 shown):

```
E2  Product (RWF)     =C2*Assumptions!$B$3
F2  Shipping (RWF)    =MAX(D2*Assumptions!$B$7,Assumptions!$B$8)
G2  Duty rate         =INDEX(Assumptions!$B$12:$B$16,MATCH(B2,Assumptions!$A$12:$A$16,0))
H2  Duty (RWF)        =(E2+F2)*G2
I2  VAT (RWF)         =(E2+F2+H2)*Assumptions!$B$6
J2  Commission (RWF)  =E2*Assumptions!$B$4
K2  Buffer (RWF)      =(E2+F2)*Assumptions!$B$5
L2  DOOR PRICE (RWF)  =CEILING(E2+F2+H2+I2+J2+K2,Assumptions!$B$9)
```

**Pre-launch validation columns** (weeks 3–4 of the 90-day plan): fill `M` (Kigali market price) and `N` (AliExpress landed cost) per item, and `O` flags the result:

```
O2  Price check       =IF(M2="","fill market price",IF(L2<=M2*1.1,"OK","TOO HIGH"))
```

If a category comes back `TOO HIGH`, adjust its commission per category rather than hiding costs — the all-in price stays honest.

## Worked example — COSRX Snail Essence (₩12,900 · 180 g · skincare)

| Component | RWF |
|-----------|----:|
| Product (12,900 × 1.05) | 13,545 |
| Commission (30%) | 4,064 |
| Shipping (180 g × 11) | 1,980 |
| Duty (25% of 15,525) | 3,881 |
| VAT (18% of 19,406) | 3,493 |
| Buffer (5% of 15,525) | 776 |
| **Door price (rounded ↑ 500)** | **28,000** |

Commission is ~14.5% of the door price — the customer sees one clean number, and the business still earns its 30% on product.
