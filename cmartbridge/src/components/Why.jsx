import { useT } from '../i18n.js'
import { useReveal } from '../hooks/useReveal.js'

const CARDS = [
  { icon: '🇰🇷', t: 'why1t', d: 'why1d' },
  { icon: '📲', t: 'why2t', d: 'why2d' },
  { icon: '🏷️', t: 'why3t', d: 'why3d' },
  { icon: '🤝', t: 'why4t', d: 'why4d' },
]

export default function Why() {
  const t = useT()
  const ref = useReveal()

  return (
    <section className="section" id="why">
      <h2>{t('whyTitle')}</h2>
      <div className="card-grid reveal" ref={ref}>
        {CARDS.map((c) => (
          <article className="card" key={c.t}>
            <span className="card-icon" aria-hidden="true">
              {c.icon}
            </span>
            <h3>{t(c.t)}</h3>
            <p>{t(c.d)}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
