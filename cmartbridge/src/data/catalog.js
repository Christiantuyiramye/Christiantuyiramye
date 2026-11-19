// Phase 1 starter catalog — 20 small, light, high-demand, legally simple items.
// Prices are Korean retail estimates (Coupang / Olive Young / Dongdaemun) —
// re-check before quoting. Door prices are computed live from lib/pricing.js.
// Excluded by policy: lithium batteries, food/supplements, oversize liquids,
// restricted imports, anything over ~2 kg.

export const CATALOG = [
  // — Korean skincare & cosmetics —
  { id: 'cosrx-snail', name: 'COSRX Advanced Snail 96 Mucin Essence 100ml', category: 'skincare', priceKrw: 12900, weightG: 180 },
  { id: 'boj-sun', name: 'Beauty of Joseon Relief Sun SPF50+ 50ml', category: 'skincare', priceKrw: 11000, weightG: 90 },
  { id: 'anua-toner', name: 'Anua Heartleaf 77% Soothing Toner 250ml', category: 'skincare', priceKrw: 18000, weightG: 330 },
  { id: 'mediheal-masks', name: 'Mediheal Sheet Masks (10-pack)', category: 'skincare', priceKrw: 8900, weightG: 350 },
  { id: 'laneige-lip', name: 'Laneige Lip Sleeping Mask 20g', category: 'skincare', priceKrw: 17000, weightG: 60 },
  { id: 'etude-brow', name: 'Etude Drawing Eye Brow Pencil', category: 'skincare', priceKrw: 4000, weightG: 20 },

  // — Phone accessories (no lithium batteries) —
  { id: 'clear-case', name: 'Clear shockproof phone case (iPhone/Samsung)', category: 'phone-accessories', priceKrw: 6000, weightG: 60 },
  { id: 'glass-2pk', name: 'Tempered glass screen protector (2-pack)', category: 'phone-accessories', priceKrw: 5000, weightG: 80 },
  { id: 'usbc-cable', name: 'Fast-charge USB-C cable 1m (Samsung-grade)', category: 'phone-accessories', priceKrw: 7000, weightG: 60 },
  { id: 'wall-charger', name: '25W USB-C wall charger (genuine, no battery)', category: 'phone-accessories', priceKrw: 15000, weightG: 100 },

  // — Fashion accessories (Dongdaemun) —
  { id: 'earrings-set', name: 'Korean minimalist earrings set (3 pairs)', category: 'fashion', priceKrw: 8000, weightG: 30 },
  { id: 'claw-clips', name: 'Hair claw clips, Seoul style (set of 4)', category: 'fashion', priceKrw: 6000, weightG: 90 },
  { id: 'socks-5pk', name: 'Korean ankle socks (5-pack)', category: 'fashion', priceKrw: 7500, weightG: 150 },
  { id: 'bucket-hat', name: 'Seoul street-fashion bucket hat', category: 'fashion', priceKrw: 12000, weightG: 120 },

  // — K-pop merch —
  { id: 'photocard', name: 'Official K-pop photocard (single, sleeved)', category: 'kpop', priceKrw: 8000, weightG: 10 },
  { id: 'kpop-album', name: 'Official K-pop album (photocards included)', category: 'kpop', priceKrw: 22000, weightG: 450 },
  { id: 'pc-binder', name: 'Photocard binder + 50 sleeves', category: 'kpop', priceKrw: 12000, weightG: 250 },

  // — Stationery —
  { id: 'gel-pens', name: 'Korean gel pen set (10 colours)', category: 'stationery', priceKrw: 8000, weightG: 120 },
  { id: 'deco-stickers', name: 'Deco sticker pack (20 sheets)', category: 'stationery', priceKrw: 6000, weightG: 60 },
  { id: 'journal', name: 'Hardcover journal, Korean design', category: 'stationery', priceKrw: 9500, weightG: 280 },
]

export const CATEGORY_LABELS = {
  skincare: { en: 'K-Beauty & Skincare', rw: 'Ibikoresho byo kwisiga (K-Beauty)' },
  'phone-accessories': { en: 'Phone Accessories', rw: 'Ibikoresho bya telefoni' },
  fashion: { en: 'Fashion Accessories', rw: 'Imitako n’imyambarire' },
  kpop: { en: 'K-pop Merch', rw: 'Ibya K-pop' },
  stationery: { en: 'Stationery', rw: 'Ibikoresho byo kwandika' },
}
