import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { searchCatalog } from '../lib/search.js'
import { waLink } from '../data/site.js'
import { useReveal } from '../hooks/useReveal.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'
import Icon from './Icon.jsx'

export default function Catalog() {
  const t = useT()
  const { lang } = useLang()
  const fx = useFx()
  const cart = useCart()
  const [addedId, setAddedId] = useState(null)
  // Category and search both live in the URL, so the Products menu and the
  // header search can link straight to a filtered view.
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get('category')
  const filter = requested && CATEGORY_LABELS[requested] ? requested : 'all'
  const query = (searchParams.get('q') ?? '').trim()

  const updateParams = (change) => {
    const next = new URLSearchParams(searchParams)
    change(next)
    setSearchParams(next, { replace: true, preventScrollReset: true })
  }

  const setFilter = (key) =>
    updateParams((next) => (key === 'all' ? next.delete('category') : next.set('category', key)))

  const clearQuery = () => updateParams((next) => next.delete('q'))

  const ref = useReveal()

  const items = useMemo(
    () =>
      searchCatalog(query)
        .filter((p) => filter === 'all' || p.category === filter)
        .map((p) => ({
          ...p,
          doorPrice: landedCost(p.priceKrw, p.weightG, p.category, {
            ...CONFIG,
            krwToRwf: fx.rate,
          }).doorPrice,
        })),
    [query, filter, fx.rate],
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

      {query && (
        <p className="search-summary" role="status">
          <Icon name="search" strokeWidth={1.9} />
          <span>
            <strong>{items.length}</strong>{' '}
            {t(items.length === 1 ? 'searchResultOne' : 'searchResultMany')} “{query}”
          </span>
          <button className="link-btn" onClick={clearQuery}>
            {t('searchClear')}
          </button>
        </p>
      )}

      {items.length === 0 ? (
        <div className="catalog-empty">
          <p>{t('searchNone')}</p>
          <Link className="btn btn-primary" to={`/?want=${encodeURIComponent(query)}#request`}>
            {t('searchRequest')}
          </Link>
        </div>
      ) : (
        <div className="product-grid reveal" ref={ref}>
          {items.map((p) => (
            <article className="product" key={p.id}>
              {/* Duplicate of the title link, so kept out of the tab order and
                  hidden from screen readers. */}
              <Link
                to={`/product/${p.id}`}
                className={`product-media cat-tile cat--${p.category}`}
                tabIndex={-1}
                aria-hidden="true"
              >
                <Icon name={p.category} strokeWidth={1.5} />
              </Link>
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
                  href={waLink(
                    `Muraho CmartBridge! I want to order: ${p.name} (~${fmtRwf(p.doorPrice)}).`,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t('requestItem')}
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
