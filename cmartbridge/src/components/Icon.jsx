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
