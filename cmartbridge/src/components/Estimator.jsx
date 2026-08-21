import { useMemo, useState } from 'react'
import { useLang, useT } from '../i18n.js'
import { CATEGORIES, landedCost, fmtRwf } from '../lib/pricing.js'
import { CATEGORY_LABELS } from '../data/catalog.js'

export default function Estimator() {
  const t = useT()
  const { lang } = useLang()
  const [priceKrw, setPriceKrw] = useState(10000)
  const [weightG, setWeightG] = useState(200)
  const [category, setCategory] = useState('skincare')
  const [showBreakdown, setShowBreakdown] = useState(false)

  const cost = useMemo(
    () => landedCost(Number(priceKrw) || 0, Number(weightG) || 0, category),
    [priceKrw, weightG, category],
  )

  const rows = [
    ['bdProduct', cost.product],
    ['bdCommission', cost.commission],
    ['bdShipping', cost.shipping],
    ['bdDuty', cost.duty],
    ['bdVat', cost.vat],
    ['bdBuffer', cost.buffer],
  ]

  return (
    <section className="section section-alt" id="estimator">
      <h2>{t('estTitle')}</h2>
      <p className="section-sub">{t('estSub')}</p>

      <div className="estimator">
        <div className="estimator-inputs">
          <label>
            {t('estPriceLabel')}
            <input
              type="number"
              min="0"
              step="1000"
              value={priceKrw}
              onChange={(e) => setPriceKrw(e.target.value)}
            />
          </label>
          <label>
            {t('estWeightLabel')}
            <input
              type="number"
              min="0"
              step="50"
              value={weightG}
              onChange={(e) => setWeightG(e.target.value)}
            />
          </label>
          <label>
            {t('estCategoryLabel')}
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {Object.keys(CATEGORIES).map((key) => (
                <option key={key} value={key}>
                  {CATEGORY_LABELS[key][lang]}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="estimator-result" aria-live="polite">
          <span>{t('estResult')}</span>
          <strong key={cost.doorPrice} className="pop">
            {fmtRwf(cost.doorPrice)}
          </strong>
          <button className="link-btn" onClick={() => setShowBreakdown((v) => !v)}>
            {showBreakdown ? t('estHide') : t('estBreakdown')}
          </button>

          {showBreakdown && (
            <table className="breakdown">
              <tbody>
                {rows.map(([key, value]) => (
                  <tr key={key}>
                    <td>{t(key)}</td>
                    <td>{fmtRwf(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="fine-print">{t('estDisclaimer')}</p>
        </div>
      </div>
    </section>
  )
}
