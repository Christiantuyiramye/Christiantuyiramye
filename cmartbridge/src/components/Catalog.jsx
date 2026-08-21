import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { waLink } from '../data/site.js'
import { useReveal } from '../hooks/useReveal.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'

export default function Catalog() {
  const t = useT()
  const { lang } = useLang()
  const fx = useFx()
  const cart = useCart()
  const [filter, setFilter] = useState('all')
  const [addedId, setAddedId] = useState(null)
  const ref = useReveal()

  const items = useMemo(
    () =>
      CATALOG.filter((p) => filter === 'all' || p.category === filter).map((p) => ({
        ...p,
        doorPrice: landedCost(p.priceKrw, p.weightG, p.category, {
          ...CONFIG,
          krwToRwf: fx.rate,
        }).doorPrice,
      })),
    [filter, fx.rate],
  )

  return (
    <section className="section" id="catalog">
      <h2>{t('catalogTitle')}</h2>
      <p className="section-sub">{t('catalogSub')}</p>

      <div className="filters" role="group" aria-label="Category filter">
        <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>
          {t('all')}
        </button>
        {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
          <button
            key={key}
            className={filter === key ? 'active' : ''}
            onClick={() => setFilter(key)}
          >
            {label[lang]}
          </button>
        ))}
      </div>

      <div className="product-grid reveal" ref={ref}>
        {items.map((p) => (
          <article className="product" key={p.id}>
            <span className="product-cat">{CATEGORY_LABELS[p.category][lang]}</span>
            <Link to={`/product/${p.id}`}>
              <h3>{p.name}</h3>
            </Link>
            <p className="product-price">
              {fmtRwf(p.doorPrice)} <small>· {t('estDoorPrice')}</small>
            </p>
            <div className="product-actions">
              <button
                className="btn btn-small"
                onClick={() => {
                  cart.add(p.id, 1)
                  setAddedId(p.id)
                }}
              >
                {addedId === p.id ? t('pdpAdded') : t('pdpAddToCart')}
              </button>
              <a
                className="link-btn"
                href={waLink(`Muraho CmartBridge! I want to order: ${p.name} (~${fmtRwf(p.doorPrice)}).`)}
                target="_blank"
                rel="noreferrer"
              >
                {t('requestItem')}
              </a>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
