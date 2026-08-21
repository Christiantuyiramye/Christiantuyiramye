import { Router } from 'express'
import crypto from 'node:crypto'
import { computeTrustedOrder, normalizeMsisdn, CartValidationError } from './cart.js'
import { requestToPay, getRequestToPayStatus } from './momo.js'

const router = Router()

const MOMO_CURRENCY = process.env.MOMO_CURRENCY || 'EUR'

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

  const now = Date.now()
  const existing = pendingByPhone.get(payerMsisdn)
  if (existing && now - existing.createdAt < PENDING_TTL_MS) {
    return res.json(existing.response)
  }

  const referenceId = crypto.randomUUID()
  const itemSummary = order.lines.map((l) => `${l.product.name} x${l.qty}`).join(', ')

  try {
    await requestToPay({
      amount: order.subtotal,
      currency: MOMO_CURRENCY,
      referenceId,
      payerMsisdn,
      payerMessage: `CmartBridge order: ${itemSummary}`.slice(0, 160),
      payeeNote: `CmartBridge order for ${name || 'customer'}`.slice(0, 160),
    })
  } catch {
    return res.status(502).json({ error: 'momo_unavailable' })
  }

  const response = {
    referenceId,
    amount: order.subtotal,
    currency: MOMO_CURRENCY,
    lines: order.lines.map((l) => ({
      id: l.id,
      name: l.product.name,
      qty: l.qty,
      lineTotal: l.lineTotal,
    })),
  }

  pendingByPhone.set(payerMsisdn, { createdAt: now, response })
  setTimeout(() => pendingByPhone.delete(payerMsisdn), PENDING_TTL_MS)

  res.json(response)
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
