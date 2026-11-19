// Cart line/subtotal math — the ONE place cart pricing is computed, imported by
// both the frontend (display) and the backend (the actual MoMo charge), so there
// is never a second implementation of the money math that could drift from this one.
import { CATALOG } from '../data/catalog.js'
import { CONFIG, landedCost } from './pricing.js'

export function cartLines(items, fxRate) {
  return items
    .map((line) => {
      const product = CATALOG.find((p) => p.id === line.id)
      if (!product) return null // stale/unknown id — silently dropped
      const cost = landedCost(product.priceKrw, product.weightG, product.category, {
        ...CONFIG,
        krwToRwf: fxRate,
      })
      return {
        id: line.id,
        qty: line.qty,
        product,
        unitDoorPrice: cost.doorPrice,
        lineTotal: cost.doorPrice * line.qty,
      }
    })
    .filter(Boolean)
}

export const cartSubtotal = (lines) => lines.reduce((sum, l) => sum + l.lineTotal, 0)
