import { useState } from 'react'
import { useT } from '../i18n.js'
import { waLink } from '../data/site.js'

export default function RequestForm() {
  const t = useT()
  const [name, setName] = useState('')
  const [item, setItem] = useState('')
  const [qty, setQty] = useState(1)

  const message =
    `Muraho CmartBridge! New request:\n` +
    `• Name: ${name || '—'}\n` +
    `• Item: ${item || '—'}\n` +
    `• Quantity: ${qty}\n` +
    `Please send me an all-in door price. Murakoze!`

  return (
    <section className="section" id="request">
      <h2>{t('reqTitle')}</h2>
      <p className="section-sub">{t('reqSub')}</p>

      <form
        className="request-form"
        onSubmit={(e) => {
          e.preventDefault()
          window.open(waLink(message), '_blank', 'noreferrer')
        }}
      >
        <label>
          {t('reqName')}
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          {t('reqItem')}
          <textarea
            value={item}
            onChange={(e) => setItem(e.target.value)}
            rows={3}
            placeholder="https://www.coupang.com/… / COSRX snail essence…"
            required
          />
        </label>
        <label className="qty">
          {t('reqQty')}
          <input
            type="number"
            min="1"
            max="50"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
        </label>
        <button className="btn btn-primary" type="submit">
          {t('reqSend')}
        </button>
        <p className="fine-print">{t('reqNote')}</p>
      </form>
    </section>
  )
}
