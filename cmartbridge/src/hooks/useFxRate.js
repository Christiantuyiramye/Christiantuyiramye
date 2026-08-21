// Live KRW→RWF exchange rate, fetched client-side from a free, no-key FX API.
// Falls back to CONFIG.krwToRwf (pricing.js) if the fetch fails or is stale —
// door prices always compute, live or offline.
import { useEffect, useState } from 'react'
import { CONFIG } from '../lib/pricing.js'

const CACHE_KEY = 'cmartbridge_fx_krw_rwf_v1'
const CACHE_TTL_MS = 12 * 60 * 60 * 1000 // 12h — matches typical daily FX API refresh
const API_URL = 'https://open.er-api.com/v6/latest/KRW'

function readCache() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CACHE_KEY))
    if (!parsed?.rate || !parsed?.fetchedAt) return null
    return parsed
  } catch {
    return null
  }
}

function writeCache(rate) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ rate, fetchedAt: Date.now() }))
  } catch {
    // localStorage unavailable (private mode, quota) — rate just won't persist across reloads
  }
}

export function useFxRate() {
  const cached = readCache()
  const [state, setState] = useState({
    rate: cached?.rate ?? CONFIG.krwToRwf,
    source: cached ? 'cached' : 'fallback',
    updatedAt: cached?.fetchedAt ?? null,
    loading: true,
  })

  useEffect(() => {
    if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
      setState((s) => ({ ...s, loading: false }))
      return
    }

    let cancelled = false
    fetch(API_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`FX API responded ${res.status}`)
        return res.json()
      })
      .then((data) => {
        const rate = data?.rates?.RWF
        if (cancelled) return
        if (typeof rate === 'number' && rate > 0) {
          writeCache(rate)
          setState({ rate, source: 'live', updatedAt: Date.now(), loading: false })
        } else {
          setState((s) => ({ ...s, loading: false }))
        }
      })
      .catch(() => {
        if (!cancelled) setState((s) => ({ ...s, loading: false }))
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return state
}
