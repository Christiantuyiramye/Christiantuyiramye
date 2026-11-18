// The initial theme is applied by the inline script in index.html before React
// loads; this hook takes it over from there.
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'cmart-theme'
const THEME_COLORS = { light: '#f2f0ea', dark: '#0a0a0a' }

function readSaved() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'light' || saved === 'dark' ? saved : null
  } catch {
    return null
  }
}

export function useThemeState() {
  const [theme, setTheme] = useState(() =>
    document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light',
  )
  const [hasChoice, setHasChoice] = useState(() => readSaved() !== null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme])
  }, [theme])

  // Follow the device setting live until the visitor picks a theme themselves.
  useEffect(() => {
    if (hasChoice) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e) => setTheme(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [hasChoice])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setHasChoice(true)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Private mode or blocked storage: the toggle still works for this visit.
    }
  }

  return { theme, toggleTheme }
}
