import { Router } from 'express'
import crypto from 'node:crypto'
import { computeTrustedOrder, normalizeMsisdn, CartValidationError } from './cart.js'
import { requestToPay, getRequestToPayStatus } from './momo.js'
import { getSandboxEurPerRwf } from './fx.js'

const router = Router()

// MTN's sandbox only accepts EUR; every real (mtnrwanda) charge is RWF. Deriving
// the currency from the environment means production can never be charged in the
// wrong currency because of a forgotten setting.
const IS_SANDBOX = process.env.MOMO_TARGET_ENVIRONMENT === 'sandbox'
const CHARGE_CURRENCY = IS_SANDBOX ? 'EUR' : 'RWF'

async function chargeAmount(subtotalRwf) {
  if (!IS_SANDBOX) return subtotalRwf
  const eurPerRwf = await getSandboxEurPerRwf()
  return Math.max(0.01, Math.round(subtotalRwf * eurPerRwf * 100) / 100)
}

// Duplicate-submit guard: one in-flight request per phone number, so a double
// click (or client retry) can't fire two MoMo payment prompts for one checkout.
const pendingByPhone = new Map()
const PENDING_TTL_MS = 2 * 60 * 1000

function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}

router.post('/momo/pay', async (req, res) => {
  const { cart, phone, name, note } = req.body || {}

  let order
  let payerMsisdn
  try {
    order = await computeTrustedOrder(cart)
    payerMsisdn = normalizeMsisdn(phone)
  } catch (err) {
    if (err instanceof CartValidationError) {
      return res.status(400).json({ error: err.code, detail: err.detail })
    }
    return res.status(400).json({ error: 'invalid_request' })
  }

  const charged = { amount: await chargeAmount(order.subtotal), currency: CHARGE_CURRENCY }

  // No await between this check and the reservation below, so a concurrent
  // duplicate always sees the reservation. A duplicate waits on the original
  // request and gets the same reference, rather than prompting the phone again.
  const now = Date.now()
  const existing = pendingByPhone.get(payerMsisdn)
  if (existing && now - existing.createdAt < PENDING_TTL_MS) {
    try {
      return res.json(await existing.response)
    } catch {
      return res.status(502).json({ error: 'momo_unavailable' })
    }
  }

  const referenceId = crypto.randomUUID()
  const itemSummary = order.lines.map((l) => `${l.product.name} x${l.qty}`).join(', ')

  const entry = {
    createdAt: now,
    response: requestToPay({
      amount: charged.amount,
      currency: charged.currency,
      referenceId,
      payerMsisdn,
      payerMessage: `CmartBridge order: ${itemSummary}`.slice(0, 160),
      payeeNote: `CmartBridge order for ${name || 'customer'}`.slice(0, 160),
    }).then(() => ({
      referenceId,
      amount: order.subtotal, // RWF: the price the customer was quoted
      charged,
      lines: order.lines.map((l) => ({
        id: l.id,
        name: l.product.name,
        qty: l.qty,
        lineTotal: l.lineTotal,
      })),
    })),
  }

  // Only ever removes this request's own entry, never a newer one for the phone.
  const release = () => {
    if (pendingByPhone.get(payerMsisdn) === entry) pendingByPhone.delete(payerMsisdn)
  }
  pendingByPhone.set(payerMsisdn, entry)
  setTimeout(release, PENDING_TTL_MS)

  try {
    res.json(await entry.response)
  } catch {
    release() // MTN didn't confirm the request, so let the customer retry straight away
    res.status(502).json({ error: 'momo_unavailable' })
  }
})

router.get('/momo/status/:referenceId', async (req, res) => {
  const { referenceId } = req.params
  if (!isUuid(referenceId)) {
    return res.status(400).json({ error: 'invalid_reference' })
  }

  try {
    const status = await getRequestToPayStatus(referenceId)
    res.json(status)
  } catch {
    res.status(502).json({ error: 'momo_unavailable' })
  }
})

export default router
