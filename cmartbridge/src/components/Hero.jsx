import { useT } from '../i18n.js'
import { waLink } from '../data/site.js'

export default function Hero() {
  const t = useT()

  return (
    <section className="hero" id="top">
      <div className="hero-inner">
        <h1 className="fade-up">{t('heroTitle')}</h1>
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
          <a className="btn btn-ghost" href="#catalog">
            {t('ctaCatalog')}
          </a>
        </div>
        <ul className="hero-badges fade-up delay-3">
          <li>✅ {t('allInBadge')}</li>
          <li>📱 {t('momoBadge')}</li>
          <li>📸 {t('photoBadge')}</li>
        </ul>
      </div>
    </section>
  )
}
