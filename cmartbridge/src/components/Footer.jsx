import { useT } from '../i18n.js'
import { SITE, waLink } from '../data/site.js'
import Icon from './Icon.jsx'

export default function Footer() {
  const t = useT()

  return (
    <footer className="footer">
      <p className="footer-tag">{t('footerTag')}</p>
      <nav className="footer-links">
        <a href={waLink('Muraho CmartBridge!')} target="_blank" rel="noreferrer">
          <Icon name="chat" /> WhatsApp
        </a>
        <a href={`https://instagram.com/${SITE.instagram}`} target="_blank" rel="noreferrer">
          <Icon name="instagram" /> {SITE.instagram}
        </a>
        <a href={`mailto:${SITE.email}`}>
          <Icon name="mail" /> {SITE.email}
        </a>
      </nav>
      <p className="fine-print">{t('footerPhase')}</p>
      <p className="fine-print">© {new Date().getFullYear()} CmartBridge Rwanda</p>
    </footer>
  )
}
