import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { CATEGORY_LABELS } from '../data/catalog.js'
import { waLink } from '../data/site.js'
import CartBadge from './CartBadge.jsx'

const WA_MESSAGE = 'Muraho CmartBridge! I would like to order from Korea.'

// Below this width the links collapse into the drawer (matches the CSS breakpoint).
const MOBILE_QUERY = '(max-width: 900px)'

export default function Header() {
  const { lang, setLang } = useLang()
  const t = useT()
  const { pathname, hash } = useLocation()
  const isHome = pathname === '/'

  const headerRef = useRef(null)
  // "Over" = transparent bar floating on the dark hero. Only ever true on the
  // home page, and only until the hero has scrolled past.
  const [over, setOver] = useState(isHome)
  const [openMenu, setOpenMenu] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  // A menu opened by hover must not be closed by the click that follows it.
  const openedByHover = useRef(false)

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
  }, [pathname, hash])

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
    if (!openMenu && !drawerOpen) return
    const onPointerDown = (e) => {
      if (!headerRef.current?.contains(e.target)) setOpenMenu(null)
    }
    const onKeyDown = (e) => {
      if (e.key !== 'Escape') return
      setOpenMenu(null)
      setDrawerOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [openMenu, drawerOpen])

  useEffect(() => {
    if (!drawerOpen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [drawerOpen])

  const menus = [
    {
      id: 'why',
      label: t('navWhy'),
      links: [
        { to: '/#why', label: t('navWhyUs'), desc: t('navWhyUsDesc') },
        { to: '/#how', label: t('navHow'), desc: t('navHowDesc') },
        { to: '/#terms', label: t('navPromises'), desc: t('navPromisesDesc') },
      ],
    },
    {
      id: 'products',
      label: t('navProducts'),
      links: [
        { to: '/#catalog', label: t('navAllProducts'), desc: t('navAllProductsDesc') },
        ...Object.entries(CATEGORY_LABELS).map(([key, label]) => ({
          to: `/?category=${key}#catalog`,
          label: label[lang],
        })),
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
  }

  const canHover = () => window.matchMedia('(hover: hover)').matches

  const openOnHover = (id) => {
    if (!canHover()) return
    openedByHover.current = true
    setOpenMenu(id)
  }

  const closeOnHover = (id) => {
    if (!canHover()) return
    setOpenMenu((current) => (current === id ? null : current))
  }

  const toggleMenu = (id) => {
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

  return (
    <>
      <header
        ref={headerRef}
        className={`header${over && !drawerOpen ? ' header--over' : ''}`}
      >
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
                onMouseEnter={() => openOnHover(menu.id)}
                onMouseLeave={() => closeOnHover(menu.id)}
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
                  <div className="nav-panel">
                    {menu.links.map((link) => (
                      <Link key={link.to} to={link.to} onClick={closeAll}>
                        {link.label}
                        {link.desc && <small>{link.desc}</small>}
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
          <div className="lang-toggle" role="group" aria-label={t('navLanguage')}>
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
            onClick={() => setDrawerOpen((open) => !open)}
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
