import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { searchCatalog, SEARCH_SUGGESTIONS } from '../lib/search.js'
import { useFx } from '../fx.js'
import Icon from './Icon.jsx'

const MAX_RESULTS = 6

// Open/closed state lives in Header, which also needs it to switch the bar solid
// and to close the other menus.
export default function HeaderSearch({ open, onOpenChange }) {
  const t = useT()
  const { lang } = useLang()
  const fx = useFx()
  const navigate = useNavigate()
  const [term, setTerm] = useState('')
  const inputRef = useRef(null)
  const toggleRef = useRef(null)
  const panelRef = useRef(null)

  // The last query is kept but selected, so typing replaces it rather than
  // appending to it, while it's still there to refine.
  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [open])

  const query = term.trim()
  const matches = useMemo(() => (query ? searchCatalog(query) : []), [query])
  const results = matches.slice(0, MAX_RESULTS).map((p) => ({
    ...p,
    doorPrice: landedCost(p.priceKrw, p.weightG, p.category, { ...CONFIG, krwToRwf: fx.rate })
      .doorPrice,
  }))

  const close = (restoreFocus = false) => {
    onOpenChange(false)
    if (restoreFocus) toggleRef.current?.focus()
  }

  const submit = (e) => {
    e.preventDefault()
    if (!query) return
    close()
    navigate(`/?q=${encodeURIComponent(query)}#catalog`)
  }

  // Arrow keys walk input → suggestions/results → back to input.
  const onPanelKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      close(true)
      return
    }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    const items = [...(panelRef.current?.querySelectorAll('[data-result]') ?? [])]
    if (items.length === 0) return
    e.preventDefault()
    const index = items.indexOf(document.activeElement)
    if (e.key === 'ArrowDown') items[Math.min(index + 1, items.length - 1)].focus()
    else if (index <= 0) inputRef.current?.focus()
    else items[index - 1].focus()
  }

  return (
    <>
      <button
        ref={toggleRef}
        type="button"
        className="search-toggle"
        aria-label={t('navSearch')}
        aria-expanded={open}
        aria-controls="site-search"
        onClick={() => onOpenChange(!open)}
      >
        <Icon name="search" strokeWidth={1.9} />
      </button>

      {open && (
        <div className="search-panel" id="site-search" ref={panelRef} onKeyDown={onPanelKeyDown}>
          <div className="search-inner">
            <form className="search-form" role="search" onSubmit={submit}>
              <Icon name="search" className="search-form-icon" strokeWidth={1.9} />
              <input
                ref={inputRef}
                type="search"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
                placeholder={t('searchPlaceholder')}
                aria-label={t('navSearch')}
                autoComplete="off"
                enterKeyHint="search"
              />
              <button
                type="button"
                className="search-close"
                aria-label={t('searchClose')}
                onClick={() => close(true)}
              >
                <Icon name="close" strokeWidth={1.9} />
              </button>
            </form>

            {!query && (
              <div className="search-suggest">
                <span className="search-suggest-label">{t('searchPopular')}</span>
                {SEARCH_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    data-result
                    onClick={() => {
                      setTerm(suggestion)
                      inputRef.current?.focus()
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {query && results.length > 0 && (
              <>
                <ul className="search-results">
                  {results.map((p) => (
                    <li key={p.id}>
                      <Link data-result to={`/product/${p.id}`} onClick={() => close()}>
                        <span className={`search-thumb cat-tile cat--${p.category}`}>
                          <Icon name={p.category} />
                        </span>
                        <span className="search-text">
                          <span className="search-name">{p.name}</span>
                          <span className="search-cat">{CATEGORY_LABELS[p.category][lang]}</span>
                        </span>
                        <span className="search-price">{fmtRwf(p.doorPrice)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <Link
                  data-result
                  className="search-all"
                  to={`/?q=${encodeURIComponent(query)}#catalog`}
                  onClick={() => close()}
                >
                  {t('searchSeeAll')} ({matches.length})
                  <Icon name="arrow" strokeWidth={1.9} />
                </Link>
              </>
            )}

            {query && results.length === 0 && (
              <div className="search-empty">
                <p>{t('searchNone')}</p>
                <Link
                  data-result
                  className="btn btn-primary"
                  to={`/?want=${encodeURIComponent(query)}#request`}
                  onClick={() => close()}
                >
                  {t('searchRequest')}: “{query}”
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
