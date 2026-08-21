import { Link, useNavigate } from 'react-router-dom'
import { useT } from '../i18n.js'
import { useFx } from '../fx.js'
import { useCart } from '../cart.js'
import { cartLines, cartSubtotal } from '../lib/cartTotals.js'
import { fmtRwf } from '../lib/pricing.js'
import { MAX_QTY_PER_LINE } from '../lib/cartLimits.js'

export default function CartPage() {
  const t = useT()
  const fx = useFx()
  const cart = useCart()
  const navigate = useNavigate()

  const lines = cartLines(cart.items, fx.rate)
  const subtotal = cartSubtotal(lines)

  if (lines.length === 0) {
    return (
      <section className="section cart-page">
        <h1>{t('cartTitle')}</h1>
        <p className="section-sub">{t('cartEmpty')}</p>
        <div className="cart-empty-cta">
          <Link className="btn btn-primary" to="/">
            {t('cartBrowse')}
          </Link>
        </div>
      </section>
    )
  }

  return (
    <section className="section cart-page">
      <h1>{t('cartTitle')}</h1>

      <ul className="cart-list">
        {lines.map((line) => (
          <li className="cart-line" key={line.id}>
            <Link className="cart-line-name" to={`/product/${line.id}`}>
              {line.product.name}
            </Link>
            <label className="qty">
              {t('reqQty')}
              <input
                type="number"
                min="1"
                max={MAX_QTY_PER_LINE}
                value={line.qty}
                onChange={(e) => cart.setQty(line.id, Number(e.target.value) || 0)}
              />
            </label>
            <span className="cart-line-total">{fmtRwf(line.lineTotal)}</span>
            <button className="link-btn" onClick={() => cart.remove(line.id)}>
              {t('cartRemove')}
            </button>
          </li>
        ))}
      </ul>

      <div className="cart-summary estimator-result">
        <span>{t('cartSubtotal')}</span>
        <strong key={subtotal} className="pop">
          {fmtRwf(subtotal)}
        </strong>
        <button className="btn btn-primary" onClick={() => navigate('/checkout')}>
          {t('cartCheckout')}
        </button>
        <p className="fine-print">{t('cartFxNote')}</p>
      </div>
    </section>
  )
}
