import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useT } from '../i18n.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'
import { cartLines, cartSubtotal } from '../lib/cartTotals.js'
import { fmtRwf } from '../lib/pricing.js'
import { waLink } from '../data/site.js'
import { useMomoCheckout } from '../hooks/useMomoCheckout.js'

export default function CheckoutPage() {
  const t = useT()
  const fx = useFx()
  const cart = useCart()
  const navigate = useNavigate()
  const momo = useMomoCheckout()

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [note, setNote] = useState('')
  const [method, setMethod] = useState('momo')
  // Cart becomes empty the instant an order completes (cart.clear()) — this flag
  // stops the empty-cart guard below from racing that clear and bouncing the user
  // back to /cart instead of letting the navigate() to /order-confirmation land.
  const [completed, setCompleted] = useState(false)

  const lines = cartLines(cart.items, fx.rate)
  const subtotal = cartSubtotal(lines)

  useEffect(() => {
    if (momo.state === 'success' && momo.order) {
      setCompleted(true)
      cart.clear()
      navigate('/order-confirmation', {
        replace: true,
        state: { order: momo.order, name, phone, note, viaMomo: true },
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [momo.state, momo.order, cart.clear, navigate])

  if (lines.length === 0 && momo.state === 'idle' && !completed) {
    return <Navigate to="/cart" replace />
  }

  const handleMomoSubmit = (e) => {
    e.preventDefault()
    momo.pay({ cart: cart.items, phone, name, note })
  }

  const handleManualSubmit = (e) => {
    e.preventDefault()
    setCompleted(true)
    const itemLines = lines
      .map((l) => `• ${l.product.name} x${l.qty} — ${fmtRwf(l.lineTotal)}`)
      .join('\n')
    const message =
      `Muraho CmartBridge! New order:\n${itemLines}\n` +
      `Total: ${fmtRwf(subtotal)}\n` +
      `Name: ${name || '—'}\nPhone: ${phone || '—'}\n` +
      (note ? `Note: ${note}\n` : '') +
      `I will pay via Airtel Money / bank transfer — please send payment details.`
    window.open(waLink(message), '_blank', 'noreferrer')
    cart.clear()
    navigate('/order-confirmation', { state: { name, phone, note, viaMomo: false, subtotal } })
  }

  const busy = momo.state === 'pending'

  return (
    <section className="section checkout-page">
      <h1>{t('coTitle')}</h1>

      <table className="breakdown checkout-summary">
        <tbody>
          {lines.map((l) => (
            <tr key={l.id}>
              <td>
                {l.product.name} × {l.qty}
              </td>
              <td>{fmtRwf(l.lineTotal)}</td>
            </tr>
          ))}
          <tr>
            <td>
              <strong>{t('cartSubtotal')}</strong>
            </td>
            <td>
              <strong>{fmtRwf(subtotal)}</strong>
            </td>
          </tr>
        </tbody>
      </table>

      <form
        className="request-form checkout-form"
        onSubmit={method === 'momo' ? handleMomoSubmit : handleManualSubmit}
      >
        <label>
          {t('coName')}
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          {t('coPhone')}
          <input
            type="tel"
            inputMode="tel"
            placeholder="078xxxxxxx"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />
        </label>
        <p className="fine-print">{t('coPhoneHint')}</p>
        <label>
          {t('coNote')}
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        </label>

        <div className="pay-methods" role="group" aria-label={t('coPayMethod')}>
          <button
            type="button"
            className={method === 'momo' ? 'pay-method active' : 'pay-method'}
            onClick={() => setMethod('momo')}
          >
            <strong>{t('coPayMomo')}</strong>
            <span>{t('coPayMomoSub')}</span>
          </button>
          <button
            type="button"
            className={method === 'manual' ? 'pay-method active' : 'pay-method'}
            onClick={() => setMethod('manual')}
          >
            <strong>{t('coPayManual')}</strong>
            <span>{t('coPayManualSub')}</span>
          </button>
        </div>

        {method === 'momo' && (
          <div className="payment-status" aria-live="polite">
            {momo.state === 'pending' && (
              <p>
                <span className="spinner" aria-hidden="true" /> {t('payPending')}
              </p>
            )}
            {(momo.state === 'failed' || momo.state === 'error') && (
              <p>
                {t('payFailed')}{' '}
                <button type="button" className="link-btn" onClick={momo.reset}>
                  {t('payRetry')}
                </button>
                {' · '}
                <button type="button" className="link-btn" onClick={() => setMethod('manual')}>
                  {t('paySwitchManual')}
                </button>
              </p>
            )}
            {momo.state === 'timeout' && (
              <p>
                {t('payTimeout')}{' '}
                <a
                  className="link-btn"
                  href={waLink(
                    `Muraho CmartBridge! I paid via MTN MoMo (reference ${momo.order?.referenceId}) but haven't seen confirmation — please check.`,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t('payAlreadyPaid')}
                </a>
              </p>
            )}
          </div>
        )}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {method === 'momo' ? t('coSubmitMomo') : t('coSubmitManual')}
        </button>
      </form>
    </section>
  )
}
