// Prints the starter catalog as a markdown table with computed door prices.
// Used to generate docs/starter-catalog.md — run `npm run catalog:print`.
import { CATALOG, CATEGORY_LABELS } from '../src/data/catalog.js'
import { landedCost, CONFIG } from '../src/lib/pricing.js'

const fmt = (n) => Math.round(n).toLocaleString('en-US')

console.log('| # | Product | Category | Korea price (KRW) | Weight (g) | Door price (RWF) |')
console.log('|---|---------|----------|------------------:|-----------:|-----------------:|')

CATALOG.forEach((p, i) => {
  const { doorPrice } = landedCost(p.priceKrw, p.weightG, p.category)
  console.log(
    `| ${i + 1} | ${p.name} | ${CATEGORY_LABELS[p.category].en} | ${fmt(p.priceKrw)} | ${p.weightG} | **${fmt(doorPrice)}** |`,
  )
})

const totals = CATALOG.reduce(
  (acc, p) => {
    const c = landedCost(p.priceKrw, p.weightG, p.category)
    acc.krw += p.priceKrw
    acc.door += c.doorPrice
    acc.commission += c.commission
    return acc
  },
  { krw: 0, door: 0, commission: 0 },
)

console.log()
console.log(
  `Assumptions: 1 KRW = ${CONFIG.krwToRwf} RWF · shipping ${CONFIG.shippingRwfPerGram} RWF/g (min ${CONFIG.minShippingRwf} RWF) · VAT ${CONFIG.vatRate * 100}% · buffer ${CONFIG.bufferRate * 100}% · rounded up to ${CONFIG.roundToRwf} RWF.`,
)
console.log(
  `One of each (20 items): Korea cost ₩${fmt(totals.krw)} · total door value ${fmt(totals.door)} RWF · commission earned ≈ ${fmt(totals.commission)} RWF.`,
)
