// Server's own trusted FX rate — same source/fallback as src/hooks/useFxRate.js,
// but this is the copy that ever actually determines a real charge.
import { CONFIG } from '../src/lib/pricing.js'

const API_URL = 'https://open.er-api.com/v6/latest/KRW'
const CACHE_TTL_MS = 10 * 60 * 1000 // 10 minutes

let cached = null // { rate, fetchedAt }

export async function getServerFxRate() {
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.rate
  }

  try {
    const res = await fetch(API_URL)
    if (!res.ok) throw new Error(`FX API responded ${res.status}`)
    const data = await res.json()
    const rate = data?.rates?.RWF
    if (typeof rate !== 'number' || rate <= 0) throw new Error('Invalid FX response')
    cached = { rate, fetchedAt: Date.now() }
    return rate
  } catch {
    return CONFIG.krwToRwf
  }
}
