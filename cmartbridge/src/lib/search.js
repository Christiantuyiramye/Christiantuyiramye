// Catalog search shared by the header's instant results and the catalog's ?q=
// filter, so both always agree on what matches.
import { CATALOG, CATEGORY_LABELS } from '../data/catalog.js'

// Words shoppers type that the product names don't contain.
const SYNONYMS = {
  'cosrx-snail': 'serum',
  'boj-sun': 'sunscreen sunblock spf',
  'mediheal-masks': 'face mask facemask',
  'laneige-lip': 'lip balm lipbalm',
  'etude-brow': 'makeup eyebrow',
  'clear-case': 'cover',
  'usbc-cable': 'charger charging cord type-c',
  'wall-charger': 'adapter plug type-c',
  'earrings-set': 'jewelry jewellery',
  'claw-clips': 'hair clip',
  'bucket-hat': 'cap',
  'photocard': 'card',
  'kpop-album': 'cd music',
  'pc-binder': 'collect book',
  'gel-pens': 'pen',
  'deco-stickers': 'stickers',
  'journal': 'notebook diary planner',
}

const INDEX = CATALOG.map((product) => ({
  product,
  haystack: [
    product.name,
    product.category,
    CATEGORY_LABELS[product.category].en,
    CATEGORY_LABELS[product.category].rw,
    SYNONYMS[product.id] ?? '',
  ]
    .join(' ')
    .toLowerCase(),
}))

/** Every word of the query must appear somewhere in the product's text. */
export function searchCatalog(query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (words.length === 0) return CATALOG
  return INDEX.filter(({ haystack }) => words.every((w) => haystack.includes(w))).map(
    ({ product }) => product,
  )
}

export const SEARCH_SUGGESTIONS = ['Snail essence', 'Sunscreen', 'K-pop album', 'Phone case', 'Earrings']
