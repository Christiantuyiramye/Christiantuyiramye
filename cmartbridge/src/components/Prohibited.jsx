import { useT } from '../i18n.js'
import { useReveal } from '../hooks/useReveal.js'

const ITEMS = ['prohib1', 'prohib2', 'prohib3', 'prohib4', 'prohib5']

export default function Prohibited() {
  const t = useT()
  const ref = useReveal()

  return (
    <section className="section section-alt" id="prohibited">
      <h2>{t('prohibTitle')}</h2>
      <p className="section-sub">{t('prohibSub')}</p>
      <ul className="prohibited-list reveal" ref={ref}>
        {ITEMS.map((key) => (
          <li key={key}>
            <span aria-hidden="true">🚫</span> {t(key)}
          </li>
        ))}
      </ul>
    </section>
  )
}
