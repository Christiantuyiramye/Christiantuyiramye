// React Router (library mode) doesn't reset scroll position on navigation the way
// a full page load does — this restores that behavior for route changes, and adds
// the hash scrolling the nav menu's section links rely on.
import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

export function useScrollToTop() {
  // `key` changes on every navigation, so a second search that lands on the same
  // /#catalog URL still scrolls back to the results.
  const { pathname, hash, key } = useLocation()
  const lastPathname = useRef(pathname)

  useEffect(() => {
    const target = hash ? document.getElementById(hash.slice(1)) : null

    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else if (lastPathname.current !== pathname) {
      // Only a real page change scrolls to the top: changing the query string
      // (the catalog's category filter) must leave the reader where they are.
      window.scrollTo(0, 0)
    }

    lastPathname.current = pathname
  }, [pathname, hash, key])
}
