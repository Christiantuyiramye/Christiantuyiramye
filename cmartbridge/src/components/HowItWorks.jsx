import { useT } from '../i18n.js'
import { useReveal } from '../hooks/useReveal.js'

// The five WhatsApp status points every order gets.
const STEPS = [
  { icon: '💳', t: 'step0t', d: 'step0d' },
  { icon: '🛍️', t: 'step1t', d: 'step1d' },
  { icon: '✈️', t: 'step2t', d: 'step2d' },
  { icon: '🛬', t: 'step3t', d: 'step3d' },
  { icon: '🏠', t: 'step4t', d: 'step4d' },
]

export default function HowItWorks() {
  const t = useT()
  const ref = useReveal()

  return (
    <section className="section section-alt" id="how">
      <h2>{t('howTitle')}</h2>
      <p className="section-sub">{t('howSub')}</p>
      <ol className="timeline reveal" ref={ref}>
        {STEPS.map((s, i) => (
          <li className="timeline-step" key={s.t} style={{ '--i': i }}>
            <span className="timeline-icon" aria-hidden="true">
              {s.icon}
            </span>
            <div>
              <h3>
                <span className="step-no">{i + 1}</span> {t(s.t)}
              </h3>
              <p>{t(s.d)}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="delivery-note">🗓️ {t('deliveryNote')}</p>
    </section>
  )
}
