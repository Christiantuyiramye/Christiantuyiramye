// Line icons drawn on a 24px grid, stroked in currentColor so they take the
// colour of whatever they sit in. Category glyphs stand in for product photos
// until real ones exist.
const GLYPHS = {
  skincare: (
    <>
      <path d="M10 6V4.3a2 2 0 0 1 4 0V6" />
      <rect x="9" y="6" width="6" height="2.3" rx="0.6" />
      <path d="M8 8.3h8l.6 1.6v9.3a2.3 2.3 0 0 1-2.3 2.3H9.7a2.3 2.3 0 0 1-2.3-2.3V9.9L8 8.3Z" />
      <path d="M7.4 13.2h9.2" />
    </>
  ),
  'phone-accessories': (
    <>
      <rect x="6.5" y="2.5" width="11" height="19" rx="2.6" />
      <path d="M10.5 18.4h3" />
    </>
  ),
  fashion: (
    <>
      <path d="M6.5 4h11L21 9l-9 11.5L3 9l3.5-5Z" />
      <path d="M3 9h18M9.5 4 7.7 9 12 20.5 16.3 9l-1.8-5" />
    </>
  ),
  kpop: (
    <>
      <path d="M9 18V5.5l11-2V16" />
      <circle cx="6.5" cy="18" r="2.5" />
      <circle cx="17.5" cy="16" r="2.5" />
    </>
  ),
  stationery: (
    <>
      <path d="M15.5 4.5l4 4L9 19l-5 1 1-5L15.5 4.5Z" />
      <path d="M13.5 6.5l4 4" />
    </>
  ),
  all: (
    <>
      <rect x="4" y="4" width="6.5" height="6.5" rx="1.5" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5" />
    </>
  ),
  star: <path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9L12 3.5Z" />,
  route: (
    <>
      <circle cx="5.5" cy="6" r="2" />
      <circle cx="18.5" cy="18" r="2" />
      <path d="M7.5 6h7a3 3 0 0 1 0 6h-5a3 3 0 0 0 0 6h7" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3l7 3v5.5c0 4.4-3 7.9-7 9.5-4-1.6-7-5.1-7-9.5V6l7-3Z" />
      <path d="M9 12l2.1 2.1L15.2 10" />
    </>
  ),
  search: (
    <>
      <circle cx="10.8" cy="10.8" r="6.3" />
      <path d="M15.6 15.6 20 20" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6 6 18" />,
  check: <path d="M5 12.5l4.3 4.3L19 7.2" />,
  arrow: <path d="M5 12h13.5M13 6.5l5.5 5.5-5.5 5.5" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" />
    </>
  ),
  moon: <path d="M20 14.6A8.2 8.2 0 0 1 9.4 4a8.2 8.2 0 1 0 10.6 10.6Z" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z" />
    </>
  ),
  wallet: (
    <>
      <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H18v3" />
      <path d="M4 7.5v10A2.5 2.5 0 0 0 6.5 20H20V8H6.5A2.5 2.5 0 0 1 4 7.5Z" />
      <path d="M16 14h.01" strokeWidth="2.6" />
    </>
  ),
  tag: (
    <>
      <path d="M3.5 12.3V4.5a1 1 0 0 1 1-1h7.8l8.2 8.2a1.5 1.5 0 0 1 0 2.1l-6.1 6.1a1.5 1.5 0 0 1-2.1 0L3.5 12.3Z" />
      <path d="M8 8h.01" strokeWidth="2.6" />
    </>
  ),
  person: (
    <>
      <circle cx="10" cy="8" r="3.6" />
      <path d="M3.5 20c.8-3.6 3.4-5.6 6.5-5.6 1.4 0 2.7.4 3.8 1.1" />
      <path d="M15.5 18.6l2 2 3.6-4.1" />
    </>
  ),
  card: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2.5" />
      <path d="M3 10h18M7 15h3" />
    </>
  ),
  bag: (
    <>
      <path d="M5 8h14l-1 11.2a2 2 0 0 1-2 1.8H8a2 2 0 0 1-2-1.8L5 8Z" />
      <path d="M9 10V7a3 3 0 0 1 6 0v3" />
    </>
  ),
  send: <path d="M21 3 10 14M21 3l-6.5 18-4-7.5L3 9.5 21 3Z" />,
  pin: (
    <>
      <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z" />
      <circle cx="12" cy="10" r="2.3" />
    </>
  ),
  home: <path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-4v-5h-5v5h-4A1.5 1.5 0 0 1 4 19v-8.5Z" />,
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </>
  ),
  ban: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M6 6l12 12" />
    </>
  ),
  chat: <path d="M4 20l1.3-3.9A8 8 0 1 1 8 18.8L4 20Z" />,
  instagram: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <path d="M17 7h.01" strokeWidth="2.6" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2.5" />
      <path d="M3.5 7l8.5 6 8.5-6" />
    </>
  ),
  truck: (
    <>
      <path d="M2.5 6h11.5v10.5H2.5Z" />
      <path d="M14 9.5h3.8l2.7 3v4H14" />
      <circle cx="7" cy="17.5" r="1.8" />
      <circle cx="17" cy="17.5" r="1.8" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
}

export default function Icon({ name, className = '', strokeWidth = 1.7 }) {
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {GLYPHS[name]}
    </svg>
  )
}
