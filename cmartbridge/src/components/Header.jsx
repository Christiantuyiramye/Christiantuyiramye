import { useLang, useT } from '../i18n.js'

export default function Header() {
  const { lang, setLang } = useLang()
  const t = useT()

  return (
    <header className="header">
      <a className="brand" href="#top">
        <span className="brand-mark">Cmart</span>Bridge
        <span className="brand-flag" aria-hidden="true">
          🇰🇷→🇷🇼
        </span>
      </a>
      <span className="header-tagline">{t('tagline')}</span>
      <div className="lang-toggle" role="group" aria-label="Language">
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
    </header>
  )
}
