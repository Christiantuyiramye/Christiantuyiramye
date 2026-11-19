import { Link } from 'react-router-dom'
import { useCart } from '../cart.js'
import { useT } from '../i18n.js'

export default function CartBadge() {
  const { count } = useCart()
  const t = useT()

  return (
    <Link className="cart-badge" to="/cart" aria-label={t('cartAria')}>
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 4h2.2l2.2 10.4a1.8 1.8 0 0 0 1.76 1.42h7.3a1.8 1.8 0 0 0 1.76-1.4L20 8H6" />
        <circle cx="10" cy="19.5" r="1.3" />
        <circle cx="17" cy="19.5" r="1.3" />
      </svg>
      {count > 0 && (
        <span className="cart-count pop" key={count}>
          {count}
        </span>
      )}
    </Link>
  )
}
