import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { waLink } from '../data/site.js'
import { useFx } from '../fx.js'
import { useTheme } from '../theme.js'
import CartBadge from './CartBadge.jsx'
import HeaderSearch from './HeaderSearch.jsx'
import Icon from './Icon.jsx'

const WA_MESSAGE = 'Muraho CmartBridge! I would like to order from Korea.'

// Below this width the links collapse into the drawer (matches the CSS breakpoint).
const MOBILE_QUERY = '(max-width: 900px)'

export default function Header() {
  const { lang, setLang } = useLang()
  const t = useT()
  const fx = useFx()
  const { theme, toggleTheme } = useTheme()
  const { pathname, hash, key } = useLocation()
  const isHome = pathname === '/'

  const headerRef = useRef(null)
  // "Over" = transparent bar floating on the dark hero. Only ever true on the
  // home page, and only until the hero has scrolled past.
  const [over, setOver] = useState(isHome)
  const [openMenu, setOpenMenu] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  // A menu opened by hover must not be closed by the click that follows it.
  const openedByHover = useRef(false)
  // Set by the arrow keys so the panel's first/last link takes focus once it renders.
  const focusOnOpen = useRef(null)

  useEffect(() => {
    if (!isHome) {
      setOver(false)
      return
    }
    let threshold = 40
    const update = () => setOver(window.scrollY < threshold)
    const measure = () => {
      const hero = document.querySelector('.hero')
      const barHeight = headerRef.current?.offsetHeight ?? 72
      threshold = hero ? Math.max(hero.offsetHeight - barHeight - 8, 40) : 40
      update()
    }
    measure()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', measure)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', measure)
    }
  }, [isHome])

  // Any navigation closes whatever is open.
  useEffect(() => {
    setOpenMenu(null)
    setDrawerOpen(false)
    setSearchOpen(false)
  }, [pathname, hash, key])

  // Leaving mobile width with the drawer open would otherwise strand it open.
  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY)
    const onChange = (e) => {
      if (!e.matches) setDrawerOpen(false)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => {
    if (!openMenu && !drawerOpen && !searchOpen) return
    const onPointerDown = (e) => {
      if (headerRef.current?.contains(e.target)) return
      setOpenMenu(null)
      setSearchOpen(false)
    }
    const onKeyDown = (e) => {
      if (e.key !== 'Escape') return
      setOpenMenu(null)
      setDrawerOpen(false)
      setSearchOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [openMenu, drawerOpen, searchOpen])

  useEffect(() => {
    if (!drawerOpen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [drawerOpen])

  useEffect(() => {
    if (!openMenu || !focusOnOpen.current) return
    const links = headerRef.current?.querySelectorAll(`[data-menu="${openMenu}"] .nav-panel a`)
    const target = focusOnOpen.current === 'last' ? links?.[links.length - 1] : links?.[0]
    focusOnOpen.current = null
    target?.focus()
  }, [openMenu])

  // Item count and cheapest door price per category, for the Products menu.
  const categoryStats = useMemo(() => {
    const stats = {}
    for (const p of CATALOG) {
      const price = landedCost(p.priceKrw, p.weightG, p.category, {
        ...CONFIG,
        krwToRwf: fx.rate,
      }).doorPrice
      const entry = (stats[p.category] ??= { count: 0, from: Infinity })
      entry.count += 1
      entry.from = Math.min(entry.from, price)
    }
    return stats
  }, [fx.rate])

  const menus = [
    {
      id: 'why',
      label: t('navWhy'),
      links: [
        { to: '/#why', label: t('navWhyUs'), desc: t('navWhyUsDesc'), icon: 'star' },
        { to: '/#how', label: t('navHow'), desc: t('navHowDesc'), icon: 'route' },
        { to: '/#terms', label: t('navPromises'), desc: t('navPromisesDesc'), icon: 'shield' },
      ],
    },
    {
      id: 'products',
      label: t('navProducts'),
      wide: true,
      links: [
        { to: '/#catalog', label: t('navAllProducts'), desc: t('navAllProductsDesc'), icon: 'all' },
        ...Object.entries(CATEGORY_LABELS).map(([category, label]) => {
          const stats = categoryStats[category]
          return {
            to: `/?category=${category}#catalog`,
            label: label[lang],
            desc: stats
              ? `${stats.count} ${t('navItemsLabel')} · ${t('navFrom')} ${fmtRwf(stats.from)}`
              : undefined,
            icon: category,
          }
        }),
      ],
    },
  ]

  const plainLinks = [
    { to: '/#estimator', label: t('navPricing') },
    { to: '/#request', label: t('navRequest') },
  ]

  const closeAll = () => {
    setOpenMenu(null)
    setDrawerOpen(false)
    setSearchOpen(false)
  }

  const changeSearchOpen = (next) => {
    setSearchOpen(next)
    if (next) {
      setOpenMenu(null)
      setDrawerOpen(false)
    }
  }

  const canHover = () => window.matchMedia('(hover: hover)').matches

  const openOnHover = (id) => {
    if (!canHover() || searchOpen) return
    openedByHover.current = true
    setOpenMenu(id)
  }

  const closeOnHover = (id) => {
    if (!canHover()) return
    setOpenMenu((current) => (current === id ? null : current))
  }

  const toggleMenu = (id) => {
    setSearchOpen(false)
    setOpenMenu((current) => {
      if (current !== id) {
        openedByHover.current = false
        return id
      }
      // Already open because the pointer is on it — the click keeps it open,
      // and the next click closes it.
      if (openedByHover.current) {
        openedByHover.current = false
        return id
      }
      return null
    })
  }

  const onMenuKeyDown = (e, id) => {
    const links = [...e.currentTarget.querySelectorAll('.nav-panel a')]
    const index = links.indexOf(document.activeElement)

    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (openMenu !== id || links.length === 0) {
        openedByHover.current = false
        focusOnOpen.current = e.key === 'ArrowUp' ? 'last' : 'first'
        setOpenMenu(id)
        return
      }
      const step = e.key === 'ArrowDown' ? 1 : -1
      const next =
        index === -1
          ? step === 1
            ? 0
            : links.length - 1
          : (index + step + links.length) % links.length
      links[next].focus()
    } else if ((e.key === 'Home' || e.key === 'End') && index !== -1) {
      e.preventDefault()
      links[e.key === 'Home' ? 0 : links.length - 1].focus()
    } else if (e.key === 'Escape' && openMenu === id) {
      e.preventDefault()
      setOpenMenu(null)
      e.currentTarget.querySelector('.nav-trigger')?.focus()
    }
  }

  // Tabbing out of a menu closes it. A null relatedTarget is a click (Safari
  // doesn't focus clicked links) — leave that to the outside-click handler, or
  // the panel would unmount before the click on its link lands.
  const onMenuBlur = (e, id) => {
    const next = e.relatedTarget
    if (next && !e.currentTarget.contains(next)) {
      setOpenMenu((current) => (current === id ? null : current))
    }
  }

  const langToggle = (className = '') => (
    <div className={`lang-toggle ${className}`} role="group" aria-label={t('navLanguage')}>
      <button
        className={lang === 'en' ? 'active' : ''}
        onClick={() => setLang('en')}
        aria-pressed={lang === 'en'}
      >
        EN
      </button>
      <button
        className={lang === 'rw' ? 'active' : ''}
        onClick={() => setLang('rw')}
        aria-pressed={lang === 'rw'}
      >
        RW
      </button>
    </div>
  )

  const panelOpen = drawerOpen || searchOpen
  const modifier = panelOpen ? ' header--opaque' : over ? ' header--over' : ''

  return (
    <>
      <header ref={headerRef} className={`header${modifier}`}>
        <Link className="brand" to="/" onClick={closeAll}>
          <svg className="brand-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 7.5h14l-1.15 12.1a2.2 2.2 0 0 1-2.19 2H8.34a2.2 2.2 0 0 1-2.19-2L5 7.5Z" />
            <path
              className="brand-icon-handle"
              d="M8.9 8.6V6.4a3.1 3.1 0 0 1 6.2 0v2.2"
              fill="none"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
          <span className="brand-word">
            <span className="brand-mark">Cmart</span>Bridge
          </span>
        </Link>

        <nav className="nav" aria-label={t('navPrimary')}>
          <ul>
            {menus.map((menu) => (
              <li
                className="nav-item"
                key={menu.id}
                data-menu={menu.id}
                onMouseEnter={() => openOnHover(menu.id)}
                onMouseLeave={() => closeOnHover(menu.id)}
                onKeyDown={(e) => onMenuKeyDown(e, menu.id)}
                onBlur={(e) => onMenuBlur(e, menu.id)}
              >
                <button
                  type="button"
                  className="nav-trigger"
                  aria-expanded={openMenu === menu.id}
                  onClick={() => toggleMenu(menu.id)}
                >
                  {menu.label}
                  <svg className="nav-caret" viewBox="0 0 10 6" aria-hidden="true">
                    <path d="M1 1l4 4 4-4" fill="none" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                </button>
                {openMenu === menu.id && (
                  <div className={`nav-panel${menu.wide ? ' nav-panel--wide' : ''}`}>
                    {menu.links.map((link) => (
                      <Link key={link.to} to={link.to} onClick={closeAll}>
                        <span className="nav-tile cat-tile">
                          <Icon name={link.icon} />
                        </span>
                        <span className="nav-panel-text">
                          {link.label}
                          {link.desc && <small>{link.desc}</small>}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </li>
            ))}
            {plainLinks.map((link) => (
              <li className="nav-item" key={link.to}>
                <Link className="nav-link" to={link.to} onClick={closeAll}>
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="header-actions">
          <HeaderSearch open={searchOpen} onOpenChange={changeSearchOpen} />

          {langToggle('lang-toggle--bar')}

          <button
            type="button"
            className="theme-toggle"
            aria-label={theme === 'dark' ? t('themeToLight') : t('themeToDark')}
            title={theme === 'dark' ? t('themeToLight') : t('themeToDark')}
            onClick={toggleTheme}
          >
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} strokeWidth={1.9} />
          </button>

          <CartBadge />

          <a className="btn-nav" href={waLink(WA_MESSAGE)} target="_blank" rel="noreferrer">
            {t('ctaOrder')}
          </a>

          <button
            type="button"
            className="nav-toggle"
            aria-expanded={drawerOpen}
            aria-controls="nav-drawer"
            aria-label={drawerOpen ? t('navClose') : t('navMenu')}
            onClick={() => {
              setSearchOpen(false)
              setDrawerOpen((open) => !open)
            }}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" strokeWidth="1.9" strokeLinecap="round">
              {drawerOpen ? (
                <>
                  <path d="M6 6l12 12" />
                  <path d="M18 6L6 18" />
                </>
              ) : (
                <>
                  <path d="M3.5 7h17" />
                  <path d="M3.5 12h17" />
                  <path d="M3.5 17h17" />
                </>
              )}
            </svg>
          </button>
        </div>
      </header>

      {/* Outside <header>: its backdrop-filter would otherwise make the header
          the containing block for this fixed panel and squash it flat. */}
      {drawerOpen && (
        <div className="nav-drawer" id="nav-drawer">
          <nav aria-label={t('navPrimary')}>
            {menus.map((menu) => (
              <section className="drawer-group" key={menu.id}>
                <h2>{menu.label}</h2>
                {menu.links.map((link) => (
                  <Link key={link.to} to={link.to} onClick={closeAll}>
                    <span className="nav-tile cat-tile">
                      <Icon name={link.icon} />
                    </span>
                    {link.label}
                  </Link>
                ))}
              </section>
            ))}
            <section className="drawer-group">
              {plainLinks.map((link) => (
                <Link key={link.to} to={link.to} onClick={closeAll}>
                  {link.label}
                </Link>
              ))}
            </section>
          </nav>
          <div className="drawer-lang">
            <span>{t('navLanguage')}</span>
            {langToggle()}
          </div>
          <a
            className="btn btn-primary drawer-cta"
            href={waLink(WA_MESSAGE)}
            target="_blank"
            rel="noreferrer"
            onClick={closeAll}
          >
            {t('ctaOrder')}
          </a>
        </div>
      )}
    </>
  )
}
