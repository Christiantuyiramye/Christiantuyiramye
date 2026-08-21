// React Router (library mode) doesn't reset scroll position on navigation the way
// a full page load does — this restores that behavior for route changes.
import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function useScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
}
