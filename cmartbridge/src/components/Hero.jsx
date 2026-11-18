import { Link } from 'react-router-dom'
import { useLang, useT } from '../i18n.js'
import { waLink } from '../data/site.js'
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'
import { CONFIG, landedCost, fmtRwf } from '../lib/pricing.js'
import { useFx } from '../fx.js'
import Icon from './Icon.jsx'

// Real catalog items at their live door prices, so the showcase doubles as a
// working entry point into the store.
const SHOWCASE_IDS = ['cosrx-snail', 'kpop-album', 'earrings-set']

const BADGES = ['allInBadge', 'momoBadge', 'photoBadge']

// The five WhatsApp updates; the card shows an order at "shipped" (index 2),
// matching the step2t label it displays.
const STATUS_STEPS = 5
const STATUS_CURRENT = 2

export default function Hero() {
  const t = useT()
  const { lang } = useLang()
  const fx = useFx()

  const showcase = SHOWCASE_IDS.map((id) => CATALOG.find((p) => p.id === id))
    .filter(Boolean)
    .map((p) => ({
      ...p,
      doorPrice: landedCost(p.priceKrw, p.weightG, p.category, { ...CONFIG, krwToRwf: fx.rate })
        .doorPrice,
    }))

  return (
    <section className="hero" id="top">
      <div className="hero-inner">
        <div className="hero-copy">
          <p className="hero-eyebrow fade-up">
            <span className="hero-eyebrow-dot" aria-hidden="true" />
            {t('heroEyebrow')}
          </p>
          <h1 className="fade-up delay-1">{t('heroTitle')}</h1>
          <p className="hero-sub fade-up delay-1">{t('heroSub')}</p>
          <div className="hero-ctas fade-up delay-2">
            <a
              className="btn btn-primary"
              href={waLink('Muraho CmartBridge! I would like to order from Korea.')}
              target="_blank"
              rel="noreferrer"
            >
              {t('ctaOrder')}
            </a>
            <Link className="btn btn-ghost" to="/#catalog">
              {t('ctaCatalog')}
            </Link>
          </div>
          <ul className="hero-badges fade-up delay-3">
            {BADGES.map((key) => (
              <li key={key}>
                <Icon name="check" strokeWidth={2.4} />
                {t(key)}
              </li>
            ))}
          </ul>
        </div>

        <div className="hero-showcase fade-up delay-2">
          <p className="showcase-label">{t('heroShowcaseLabel')}</p>
          {showcase.map((p, i) => (
            <Link
              key={p.id}
              to={`/product/${p.id}`}
              className="showcase-card"
              style={{ '--i': i }}
            >
              <span className={`showcase-media cat-tile cat--${p.category}`}>
                <Icon name={p.category} />
              </span>
              <span className="showcase-body">
                <span className="showcase-cat">{CATEGORY_LABELS[p.category][lang]}</span>
                <span className="showcase-name">{p.name}</span>
                <span className="showcase-price">{fmtRwf(p.doorPrice)}</span>
                <span className="showcase-note">{t('heroCardNote')}</span>
              </span>
            </Link>
          ))}

          <div className="showcase-status" style={{ '--i': showcase.length }} aria-hidden="true">
            <span className="status-title">
              <span className="status-pulse" />
              {t('heroStatusTitle')}
            </span>
            <ol className="status-steps">
              {Array.from({ length: STATUS_STEPS }, (_, step) => (
                <li
                  key={step}
                  className={
                    step < STATUS_CURRENT ? 'done' : step === STATUS_CURRENT ? 'current' : undefined
                  }
                />
              ))}
            </ol>
            <span className="status-label">{t('step2t')}</span>
          </div>
        </div>
      </div>
    </section>
  )
}
