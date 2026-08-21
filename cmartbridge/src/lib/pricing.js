// Landed-cost ("door price") model for CmartBridge Rwanda — Phase 1.
//
// Business rules (locked):
//   - 30% commission on product price only.
//   - Shipping, duty and VAT passed through at cost, quoted as ONE all-in
//     door price. Breakdown available on request — never hidden.
//   - ~5% buffer on product+shipping covers KRW→RWF swings and loss/reship.
//
// ALL RATES BELOW ARE PLACEHOLDERS TO VERIFY BEFORE LAUNCH:
//   - FX: krwToRwf below is the OFFLINE FALLBACK only — the live app fetches the
//     real-time rate client-side (see src/hooks/useFxRate.js) and overrides it.
//     Keep this fallback roughly current by hand in case the live fetch ever fails.
//   - Duty: EAC Common External Tariff, verify per category with RRA.
//   - Shipping: verify current Korea Post EMS rates to Rwanda.

export const CONFIG = {
  krwToRwf: 1.05, // 1 KRW in RWF — offline fallback, overridden by the live FX rate
  commissionRate: 0.3, // 30% on product price
  bufferRate: 0.05, // FX + loss buffer on (product + shipping)
  vatRate: 0.18, // Rwanda VAT
  shippingRwfPerGram: 11, // consolidated EMS allocation — verify with Korea Post
  minShippingRwf: 600, // floor for very light items (photocards, stickers)
  roundToRwf: 500, // round door price UP to the nearest…
}

// Duty rates under the EAC CET — verify with RRA before quoting.
export const CATEGORIES = {
  skincare: { duty: 0.25 },
  'phone-accessories': { duty: 0.1 },
  fashion: { duty: 0.25 },
  kpop: { duty: 0.25 },
  stationery: { duty: 0.25 },
}

/**
 * Compute the all-in door price for one item.
 * @param {number} priceKrw   retail price in Korea (KRW)
 * @param {number} weightG    packed weight in grams
 * @param {string} category   key of CATEGORIES
 * @returns breakdown in RWF + rounded door price
 */
export function landedCost(priceKrw, weightG, category, config = CONFIG) {
  const dutyRate = (CATEGORIES[category] ?? { duty: 0.25 }).duty

  const product = priceKrw * config.krwToRwf
  const shipping = Math.max(weightG * config.shippingRwfPerGram, config.minShippingRwf)
  const commission = product * config.commissionRate
  const cif = product + shipping // insurance negligible in Phase 1
  const duty = cif * dutyRate
  const vat = (cif + duty) * config.vatRate
  const buffer = cif * config.bufferRate

  const total = product + commission + shipping + duty + vat + buffer
  const doorPrice = Math.ceil(total / config.roundToRwf) * config.roundToRwf

  return { product, commission, shipping, duty, vat, buffer, total, doorPrice, dutyRate }
}

export const fmtRwf = (n) =>
  `${Math.round(n).toLocaleString('en-US')} RWF`
