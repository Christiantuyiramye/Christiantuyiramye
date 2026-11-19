// Server's own trusted FX rate — same source/fallback as src/hooks/useFxRate.js,
// but this is the copy that ever actually determines a real charge.
import { CONFIG } from '../src/lib/pricing.js'

const API_URL = 'https://open.er-api.com/v6/latest/KRW'
const CACHE_TTL_MS = 10 * 60 * 1000 // 10 minutes

// Approximate, and only ever used to turn sandbox test amounts into EUR when the
// live feed is down — real charges are RWF and never touch this.
const SANDBOX_FALLBACK_EUR_PER_RWF = 1 / 1600

let cached = null // { rates, fetchedAt } — rates are per 1 KRW

async function getRates() {
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.rates
  }

  try {
    const res = await fetch(API_URL)
    if (!res.ok) throw new Error(`FX API responded ${res.status}`)
    const data = await res.json()
    const rates = data?.rates
    if (typeof rates?.RWF !== 'number' || rates.RWF <= 0) throw new Error('Invalid FX response')
    cached = { rates, fetchedAt: Date.now() }
    return rates
  } catch {
    return null
  }
}

export async function getServerFxRate() {
  const rates = await getRates()
  return rates?.RWF ?? CONFIG.krwToRwf
}

// MTN's sandbox only accepts EUR, so test charges are converted from the RWF total.
export async function getSandboxEurPerRwf() {
  const rates = await getRates()
  if (typeof rates?.EUR === 'number' && rates.EUR > 0) return rates.EUR / rates.RWF
  return SANDBOX_FALLBACK_EUR_PER_RWF
}
