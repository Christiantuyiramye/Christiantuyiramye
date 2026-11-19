import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { MAX_QTY_PER_LINE } from '../lib/cartLimits.js'
import { waLink } from '../data/site.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'
import Icon from '../components/Icon.jsx'

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

  const categoryLabel = CATEGORY_LABELS[product.category][lang]

  return (
    <section className="section product-detail">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">{t('navHome')}</Link>
        <Link to={`/?category=${product.category}#catalog`}>{categoryLabel}</Link>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="pdp-grid">
        <div className="pdp-media cat-tile">
          <Icon name={product.category} strokeWidth={1.2} />
        </div>

        <div className="pdp-info">
          <span className="pdp-category">
            <span className="pdp-category-icon">
              <Icon name={product.category} />
            </span>
            {categoryLabel}
          </span>
          <h1>{product.name}</h1>
          <p className="pdp-price">{fmtRwf(cost.doorPrice)}</p>
          <p className="pdp-price-note">{t('pdpAllIn')}</p>

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
              <Icon name="bag" />
              {t('pdpBuyNow')}
            </button>
            <button className="btn btn-ghost" onClick={handleAdd}>
              {added ? t('pdpAdded') : t('pdpAddToCart')}
            </button>
          </div>

          <p className="pdp-delivery">
            <Icon name="truck" />
            {t('pdpDelivery')}
          </p>

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

          <a
            className="link-btn pdp-ask"
            href={waLink(`Muraho CmartBridge! I have a question about: ${product.name}.`)}
            target="_blank"
            rel="noreferrer"
          >
            {t('pdpAsk')}
          </a>
        </div>
      </div>
    </section>
  )
}
