import { Link } from 'react-router-dom'
import { useT } from '../i18n.js'

export default function NotFoundPage() {
  const t = useT()
  return (
    <section className="section not-found">
      <h1>{t('notFoundTitle')}</h1>
      <Link className="btn btn-primary" to="/">
        {t('notFoundBack')}
      </Link>
    </section>
  )
}
