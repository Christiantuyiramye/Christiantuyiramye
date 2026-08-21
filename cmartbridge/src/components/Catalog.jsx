import { useMemo, useState } from 'react'
import { useLang, useT } from '../i18n.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { landedCost, fmtRwf } from '../lib/pricing.js'
import { waLink } from '../data/site.js'
import { useReveal } from '../hooks/useReveal.js'

export default function Catalog() {
  const t = useT()
  const { lang } = useLang()
  const [filter, setFilter] = useState('all')
  const ref = useReveal()

  const items = useMemo(
    () =>
      CATALOG.filter((p) => filter === 'all' || p.category === filter).map((p) => ({
        ...p,
        doorPrice: landedCost(p.priceKrw, p.weightG, p.category).doorPrice,
      })),
    [filter],
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
            <h3>{p.name}</h3>
            <p className="product-price">
              {fmtRwf(p.doorPrice)} <small>· {t('estDoorPrice')}</small>
            </p>
            <a
              className="btn btn-small"
              href={waLink(`Muraho CmartBridge! I want to order: ${p.name} (~${fmtRwf(p.doorPrice)}).`)}
              target="_blank"
              rel="noreferrer"
            >
              {t('requestItem')}
            </a>
          </article>
        ))}
      </div>
    </section>
  )
}
