import { useT } from '../i18n.js'

const TERMS = [
  { t: 'terms1t', d: 'terms1d' },
  { t: 'terms2t', d: 'terms2d' },
  { t: 'terms3t', d: 'terms3d' },
]

export default function Terms() {
  const t = useT()

  return (
    <section className="section" id="terms">
      <h2>{t('termsTitle')}</h2>
      <div className="terms">
        {TERMS.map((item) => (
          <details key={item.t}>
            <summary>{t(item.t)}</summary>
            <p>{t(item.d)}</p>
          </details>
        ))}
      </div>
      <p className="fine-print">
        <a
          href="https://github.com/Christiantuyiramye/Christiantuyiramye/blob/main/cmartbridge/docs/terms-and-conditions.md"
          target="_blank"
          rel="noreferrer"
        >
          {t('termsLink')}
        </a>
      </p>
    </section>
  )
}
