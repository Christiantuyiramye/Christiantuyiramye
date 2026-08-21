import { Link } from 'react-router-dom'
import { useCart } from '../cart.js'
import { useT } from '../i18n.js'

export default function CartBadge() {
  const { count } = useCart()
  const t = useT()

  return (
    <Link className="cart-badge" to="/cart" aria-label={t('cartAria')}>
      <span aria-hidden="true">🛒</span>
      {count > 0 && (
        <span className="cart-count pop" key={count}>
          {count}
        </span>
      )}
    </Link>
  )
}
