// Browser-only cart state — persisted to localStorage, sanitized against the live
// CATALOG on every read/write so a stale or tampered id can never linger in the cart.
import { useCallback, useEffect, useState } from 'react'
import { CATALOG } from '../data/catalog.js'
import { MAX_QTY_PER_LINE, MAX_CART_LINES } from '../lib/cartLimits.js'

const CACHE_KEY = 'cmartbridge_cart_v1'

function sanitize(items) {
  if (!Array.isArray(items)) return []
  const catalogIds = new Set(CATALOG.map((p) => p.id))
  const seen = new Set()
  const out = []
  for (const line of items) {
    if (!line || typeof line.id !== 'string' || !catalogIds.has(line.id)) continue
    if (seen.has(line.id)) continue
    if (!Number.isFinite(line.qty)) continue
    const qty = Math.min(Math.max(Math.round(line.qty), 1), MAX_QTY_PER_LINE)
    seen.add(line.id)
    out.push({ id: line.id, qty })
    if (out.length >= MAX_CART_LINES) break
  }
  return out
}

function readCache() {
  try {
    return sanitize(JSON.parse(localStorage.getItem(CACHE_KEY)))
  } catch {
    return []
  }
}

function writeCache(items) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(items))
  } catch {
    // localStorage unavailable (private mode, quota) — cart just won't persist across reloads
  }
}

export function useCartState() {
  const [items, setItems] = useState(() => readCache())

  useEffect(() => {
    writeCache(items)
  }, [items])

  const add = useCallback((id, qty = 1) => {
    setItems((prev) => {
      const existing = prev.find((l) => l.id === id)
      const next = existing
        ? prev.map((l) => (l.id === id ? { ...l, qty: l.qty + qty } : l))
        : [...prev, { id, qty }]
      return sanitize(next)
    })
  }, [])

  const setQty = useCallback((id, qty) => {
    setItems((prev) => {
      if (qty <= 0) return prev.filter((l) => l.id !== id)
      return sanitize(prev.map((l) => (l.id === id ? { ...l, qty } : l)))
    })
  }, [])

  const remove = useCallback((id) => {
    setItems((prev) => prev.filter((l) => l.id !== id))
  }, [])

  const clear = useCallback(() => setItems([]), [])

  const count = items.reduce((sum, l) => sum + l.qty, 0)

  return { items, add, setQty, remove, clear, count }
}
