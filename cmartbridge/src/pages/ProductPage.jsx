import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { MAX_QTY_PER_LINE } from '../lib/cartLimits.js'
import { waLink } from '../data/site.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'

export default function ProductPage() {
  const { id } = useParams()
  const t = useT()
  const { lang } = useLang()
  const fx = useFx()
  const cart = useCart()
  const navigate = useNavigate()
  const [qty, setQty] = useState(1)
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [added, setAdded] = useState(false)

  const product = CATALOG.find((p) => p.id === id)
  if (!product) return <Navigate to="/" replace />

  const cost = landedCost(product.priceKrw, product.weightG, product.category, {
    ...CONFIG,
    krwToRwf: fx.rate,
  })

  const rows = [
    ['bdProduct', cost.product],
    ['bdCommission', cost.commission],
    ['bdShipping', cost.shipping],
    ['bdDuty', cost.duty],
    ['bdVat', cost.vat],
    ['bdBuffer', cost.buffer],
  ]

  const boundedQty = () => Math.min(Math.max(Number(qty) || 1, 1), MAX_QTY_PER_LINE)

  const handleAdd = () => {
    cart.add(product.id, boundedQty())
    setAdded(true)
  }

  const handleBuyNow = () => {
    cart.add(product.id, boundedQty())
    navigate('/checkout')
  }

  return (
    <section className="section product-detail">
      <Link className="link-btn" to="/">
        {t('pdpBack')}
      </Link>

      <span className="product-cat">{CATEGORY_LABELS[product.category][lang]}</span>
      <h1>{product.name}</h1>
      <p className="product-price">
        {fmtRwf(cost.doorPrice)} <small>· {t('estDoorPrice')}</small>
      </p>

      <label className="qty">
        {t('reqQty')}
        <input
          type="number"
          min="1"
          max={MAX_QTY_PER_LINE}
          value={qty}
          onChange={(e) => setQty(e.target.value)}
        />
      </label>

      <div className="product-detail-actions">
        <button className="btn btn-primary" onClick={handleBuyNow}>
          {t('pdpBuyNow')}
        </button>
        <button className="btn btn-ghost" onClick={handleAdd}>
          {added ? t('pdpAdded') : t('pdpAddToCart')}
        </button>
      </div>

      <button className="link-btn" onClick={() => setShowBreakdown((v) => !v)}>
        {showBreakdown ? t('estHide') : t('estBreakdown')}
      </button>

      {showBreakdown && (
        <table className="breakdown">
          <tbody>
            {rows.map(([key, value]) => (
              <tr key={key}>
                <td>{t(key)}</td>
                <td>{fmtRwf(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="fine-print">
        <a
          className="link-btn"
          href={waLink(`Muraho CmartBridge! I have a question about: ${product.name}.`)}
          target="_blank"
          rel="noreferrer"
        >
          {t('pdpAsk')}
        </a>
      </p>
    </section>
  )
}
