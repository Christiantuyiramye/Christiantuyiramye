// The security-critical piece: never trusts a client-sent amount. Validates the
// cart against CATALOG and the shared caps, then recomputes the total server-side
// via the SAME cartTotals.js the frontend uses for display — one implementation
// of the money math, used by an untrusted (display) caller and a trusted (charge) one.
import { CATALOG } from '../src/data/catalog.js'
import { cartLines, cartSubtotal } from '../src/lib/cartTotals.js'
import { MAX_QTY_PER_LINE, MAX_CART_LINES } from '../src/lib/cartLimits.js'
import { getServerFxRate } from './fx.js'

const MAX_TOTAL_RWF = 5_000_000
const MTN_PREFIXES = ['78', '79']

export class CartValidationError extends Error {
  constructor(code, detail) {
    super(code)
    this.code = code
    this.detail = detail
  }
}

export async function computeTrustedOrder(cart) {
  if (!Array.isArray(cart) || cart.length === 0) {
    throw new CartValidationError('empty_cart')
  }
  if (cart.length > MAX_CART_LINES) {
    throw new CartValidationError('too_many_lines')
  }

  const catalogIds = new Set(CATALOG.map((p) => p.id))
  for (const line of cart) {
    if (!line || typeof line.id !== 'string' || !catalogIds.has(line.id)) {
      throw new CartValidationError('unknown_item', line?.id)
    }
    if (!Number.isInteger(line.qty) || line.qty < 1 || line.qty > MAX_QTY_PER_LINE) {
      throw new CartValidationError('invalid_quantity', line?.id)
    }
  }

  const fxRate = await getServerFxRate()
  const lines = cartLines(cart, fxRate)
  const subtotal = cartSubtotal(lines)

  if (subtotal > MAX_TOTAL_RWF) {
    throw new CartValidationError('amount_too_large')
  }

  return { lines, subtotal, fxRate }
}

// Loose MTN-prefix hint, not a hard security gate — Rwandan numbers can be ported
// between networks, so the real gate is MTN's own API rejecting a non-MTN payer.
export function normalizeMsisdn(phone) {
  const digits = String(phone || '').replace(/\D/g, '')
  let local = digits
  if (local.startsWith('250')) local = local.slice(3)
  else if (local.startsWith('0')) local = local.slice(1)
  if (local.length !== 9) {
    throw new CartValidationError('invalid_phone')
  }
  const prefix = local.slice(0, 2)
  if (!MTN_PREFIXES.includes(prefix)) {
    throw new CartValidationError('not_mtn_number')
  }
  return `250${local}`
}
