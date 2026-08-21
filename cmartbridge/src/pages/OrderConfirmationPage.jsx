import { Link, useLocation } from 'react-router-dom'
import { useT } from '../i18n.js'
import { waLink } from '../data/site.js'
import { fmtRwf } from '../lib/pricing.js'

export default function OrderConfirmationPage() {
  const t = useT()
  const { state } = useLocation()

  if (!state) {
    return (
      <section className="section order-confirmation">
        <h1>{t('ocTitle')}</h1>
        <p className="section-sub">{t('ocFallback')}</p>
        <Link className="btn btn-primary" to="/">
          {t('cartBrowse')}
        </Link>
      </section>
    )
  }

  const { order, name, phone, note, viaMomo, subtotal } = state
  const amount = viaMomo ? order?.amount : subtotal
  const referenceId = order?.referenceId

  const message =
    `Muraho CmartBridge! My order is confirmed${viaMomo ? ' — paid via MTN MoMo' : ''}.\n` +
    (referenceId ? `Reference: ${referenceId}\n` : '') +
    `Name: ${name || '—'}\nPhone: ${phone || '—'}\n` +
    (note ? `Note: ${note}\n` : '') +
    `Total: ${amount != null ? fmtRwf(amount) : '—'}\n` +
    `Please confirm and start the order process. Murakoze!`

  return (
    <section className="section order-confirmation">
      <h1>{t('ocTitle')}</h1>

      {amount != null && (
        <p className="product-price">
          {fmtRwf(amount)} {viaMomo && order?.currency && <small>{order.currency}</small>}
        </p>
      )}
      {referenceId && (
        <p className="fine-print">
          {t('ocRefLabel')}: {referenceId}
        </p>
      )}

      <a className="btn btn-primary whatsapp-cta" href={waLink(message)} target="_blank" rel="noreferrer">
        {t('ocSendWhatsapp')}
      </a>

      <p className="section-sub">{t('ocNextSteps')}</p>
    </section>
  )
}
