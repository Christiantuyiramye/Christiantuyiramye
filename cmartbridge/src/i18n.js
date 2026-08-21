// EN / Kinyarwanda UI strings.
// Kinyarwanda drafted for launch — have a native speaker review before going live.
import { createContext, useContext } from 'react'

export const LangContext = createContext({ lang: 'en', setLang: () => {} })
export const useLang = () => useContext(LangContext)

export function useT() {
  const { lang } = useLang()
  return (key) => STRINGS[key]?.[lang] ?? STRINGS[key]?.en ?? key
}

export const STRINGS = {
  // Header / hero
  tagline: {
    en: 'Korea → Kigali, door to door',
    rw: 'Ubukoreya → Kigali, kugeza ku muryango wawe',
  },
  heroTitle: {
    en: 'Order anything from Korea. Delivered to your door in Kigali.',
    rw: 'Tumiza icyo ushaka cyose mu Bukoreya. Tukikugezaho ku muryango wawe i Kigali.',
  },
  heroSub: {
    en: 'K-beauty, K-pop merch, phone & fashion accessories — bought in Korea by a real person, quality-checked, and delivered in 2–4 weeks. One all-in price. Pay instantly with MTN MoMo, or Airtel Money/bank transfer via WhatsApp.',
    rw: 'K-beauty, ibya K-pop, ibikoresho bya telefoni n’imitako — bigurwa mu Bukoreya n’umuntu nyawe, bikagenzurwa, bikakugeraho mu byumweru 2–4. Igiciro kimwe kirimo byose. Ishyura ako kanya na MTN MoMo, cyangwa Airtel Money/banki kuri WhatsApp.',
  },
  ctaOrder: { en: 'Order on WhatsApp', rw: 'Tumiza kuri WhatsApp' },
  ctaCatalog: { en: 'See the catalog', rw: 'Reba ibicuruzwa' },
  allInBadge: { en: 'One all-in price — no surprise customs bills', rw: 'Igiciro kimwe — nta yandi mafaranga y’ikumva' },
  momoBadge: { en: 'Instant MTN MoMo checkout', rw: 'Kwishyura ako kanya na MTN MoMo' },
  photoBadge: { en: 'Photo proof before shipping', rw: 'Ifoto y’icyaguzwe mbere yo koherezwa' },

  // Why us
  whyTitle: { en: 'Why CmartBridge', rw: 'Impamvu wahitamo CmartBridge' },
  why1t: { en: 'We are in Korea', rw: 'Turi mu Bukoreya' },
  why1d: {
    en: 'Our founder buys in person from Korean-only stores and Dongdaemun wholesale — and checks quality with their own hands.',
    rw: 'Uwashinze CmartBridge agurira mu maduka yo mu Bukoreya no muri Dongdaemun, akagenzura ubuziranenge ubwe.',
  },
  why2t: { en: 'Pay with mobile money', rw: 'Yishyura na mobile money' },
  why2d: {
    en: 'No Visa or Mastercard needed. Pay instantly with MTN MoMo, or Airtel Money/bank transfer via WhatsApp — all in RWF.',
    rw: 'Ntukeneye Visa cyangwa Mastercard. Ishyura ako kanya na MTN MoMo, cyangwa Airtel Money/banki kuri WhatsApp — byose mu mafaranga y’u Rwanda.',
  },
  why3t: { en: 'One honest price', rw: 'Igiciro kimwe kizwi' },
  why3d: {
    en: 'The price we quote is the price at your door — product, shipping, customs and VAT included. Breakdown available any time you ask.',
    rw: 'Igiciro tukubwira ni cyo wishyura — igicuruzwa, ubwikorezi, imisoro byose birimo. Ushobora gusaba ibisobanuro igihe icyo ari cyo cyose.',
  },
  why4t: { en: 'A real, accountable person', rw: 'Umuntu nyawe ubazwa' },
  why4d: {
    en: 'Lost or damaged? We reship or refund in full. Every shipment is tracked.',
    rw: 'Byabuze cyangwa byangiritse? Turabisubiza cyangwa tukagusubiza amafaranga yose. Buri paki irakurikiranwa.',
  },

  // How it works / 5 status updates
  howTitle: { en: 'How it works', rw: 'Uko bikorwa' },
  howSub: {
    en: 'You get a WhatsApp update at every step — these five, every order.',
    rw: 'Ubona ubutumwa kuri WhatsApp kuri buri ntambwe — izi eshanu, kuri buri itumiza.',
  },
  step0t: { en: 'Request & pay', rw: 'Saba & wishyure' },
  step0d: {
    en: 'Send us the item on WhatsApp. We quote one all-in door price. You pay 100% upfront by MoMo — we never buy before payment clears.',
    rw: 'Twoherereza icyo ushaka kuri WhatsApp. Tukubwira igiciro kimwe kirimo byose. Wishyura byose mbere ukoresheje MoMo.',
  },
  step1t: { en: 'Purchased — with photo', rw: 'Kiguzwe — n’ifoto' },
  step1d: {
    en: 'We buy it in Korea and send you a photo of your exact item before it ships.',
    rw: 'Tukigurira mu Bukoreya tukakwoherereza ifoto y’icyo waguze mbere yo kohereza.',
  },
  step2t: { en: 'Shipped — with tracking', rw: 'Cyoherejwe — na nimero yo gukurikirana' },
  step2d: {
    en: 'Your order joins the weekly consolidated batch to Kigali. You get the tracking number.',
    rw: 'Ibyo watumije byoherezwa mu ipaki rusange ya buri cyumweru. Uhabwa nimero yo kubikurikirana.',
  },
  step3t: { en: 'Arrived in Kigali', rw: 'Byageze i Kigali' },
  step3d: {
    en: 'We tell you the moment your batch lands and enters customs clearance.',
    rw: 'Tukumenyesha ako kanya ipaki igeze i Kigali itangiye gukorerwa ibya gasutamo.',
  },
  step4t: { en: 'Cleared — out for delivery', rw: 'Byemejwe — biraje iwawe' },
  step4d: {
    en: 'Cleared with RRA, then delivered to your door or ready at the pickup point. Nothing extra to pay — ever.',
    rw: 'Bimaze kwemezwa na RRA, bikugezwaho cyangwa ubifatira aho twabikiye. Nta yandi mafaranga wishyura.',
  },
  deliveryNote: {
    en: 'Typical delivery: 2–4 weeks from payment.',
    rw: 'Ubusanzwe: ibyumweru 2–4 uhereye igihe wishyuriye.',
  },

  // Catalog
  catalogTitle: { en: 'Starter catalog', rw: 'Ibicuruzwa duhereyeho' },
  catalogSub: {
    en: 'Door prices in RWF — product, shipping, duty and VAT all included. Don’t see what you want? Request anything on WhatsApp.',
    rw: 'Ibiciro biri mu RWF — byose birimo: igicuruzwa, ubwikorezi n’imisoro. Utabonye icyo ushaka? Gisabe kuri WhatsApp.',
  },
  all: { en: 'All', rw: 'Byose' },
  estDoorPrice: { en: 'door price', rw: 'kigezweho iwawe' },
  requestItem: { en: 'Order this', rw: 'Tumiza iki' },

  // Estimator
  estTitle: { en: 'Price estimator', rw: 'Kubara igiciro' },
  estSub: {
    en: 'Found something on a Korean site? Estimate your all-in door price. Final quote confirmed on WhatsApp.',
    rw: 'Wabonye ikintu kuri site yo mu Bukoreya? Gereranya igiciro cyose. Igiciro nyacyo tukikwemeza kuri WhatsApp.',
  },
  estPriceLabel: { en: 'Price in Korea (KRW)', rw: 'Igiciro mu Bukoreya (KRW)' },
  estWeightLabel: { en: 'Weight (grams)', rw: 'Ibiro (garama)' },
  estCategoryLabel: { en: 'Category', rw: 'Icyiciro' },
  estResult: { en: 'Estimated door price', rw: 'Igiciro giteganyijwe' },
  estBreakdown: { en: 'See the breakdown', rw: 'Reba ibisobanuro' },
  estHide: { en: 'Hide breakdown', rw: 'Hisha ibisobanuro' },
  bdProduct: { en: 'Product', rw: 'Igicuruzwa' },
  bdCommission: { en: 'Our commission (30%)', rw: 'Komisiyo yacu (30%)' },
  bdShipping: { en: 'Shipping (at cost)', rw: 'Ubwikorezi (ntacyongewe)' },
  bdDuty: { en: 'Import duty (at cost)', rw: 'Umusoro wa gasutamo' },
  bdVat: { en: 'VAT 18% (at cost)', rw: 'TVA 18%' },
  bdBuffer: { en: 'FX & loss buffer (~5%)', rw: 'Ingoboka (~5%)' },
  estDisclaimer: {
    en: 'Estimate only — duty and shipping vary by item. The WhatsApp quote is final and fully guaranteed.',
    rw: 'Ni ikigereranyo — imisoro n’ubwikorezi biterwa n’igicuruzwa. Igiciro cya nyuma ni icyo tukwemereza kuri WhatsApp.',
  },
  fxChecking: { en: 'Checking live exchange rate…', rw: 'Turi kureba igiciro cy’ivunjisha…' },
  fxLive: { en: 'Live exchange rate', rw: 'Igiciro cy’ivunjisha (kya vuba)' },
  fxFallback: { en: 'Offline fallback rate', rw: 'Igiciro gishyizweho (nta interineti)' },

  // Request form
  reqTitle: { en: 'Request anything from Korea', rw: 'Saba icyo ushaka cyose mu Bukoreya' },
  reqSub: {
    en: 'Paste a link from Coupang, Gmarket or Olive Young — or just describe it. We reply with an all-in quote, usually within 24 hours.',
    rw: 'Shyiramo link ya Coupang, Gmarket cyangwa Olive Young — cyangwa ubisobanure gusa. Tugusubiza igiciro kirimo byose, akenshi mu masaha 24.',
  },
  reqName: { en: 'Your name', rw: 'Izina ryawe' },
  reqItem: { en: 'Item link or description', rw: 'Link cyangwa ibisobanuro by’igicuruzwa' },
  reqQty: { en: 'Quantity', rw: 'Umubare' },
  reqSend: { en: 'Send request on WhatsApp', rw: 'Ohereza kuri WhatsApp' },
  reqNote: {
    en: 'Opens WhatsApp with your request pre-filled — nothing is sent until you press send.',
    rw: 'Bifungura WhatsApp ubutumwa bwanditse — nta kintu twoherezwa utarabyemeza.',
  },

  // Prohibited
  prohibTitle: { en: 'What we can’t bring (yet)', rw: 'Ibyo tudashobora kuzana (kugeza ubu)' },
  prohibSub: {
    en: 'Korean export rules, airline rules and Rwandan import rules apply to every parcel. If your item is on this list we will decline politely and tell you why.',
    rw: 'Amabwiriza y’ubwikorezi n’aya gasutamo areba buri paki. Iyo igicuruzwa kiri kuri iyi lisiti, tukibwira mu buryo bwiza n’impamvu.',
  },
  prohib1: { en: 'Anything with lithium batteries (power banks, wireless earbuds, toys with batteries)', rw: 'Ibirimo batiri za lithium (power bank, earbuds, ibikinisho birimo batiri)' },
  prohib2: { en: 'Food, drinks and supplements', rw: 'Ibiribwa, ibinyobwa n’inyongera z’intungamubiri' },
  prohib3: { en: 'Liquids or aerosols over airline shipping limits', rw: 'Amazi cyangwa parufe birenze ibipimo by’indege' },
  prohib4: { en: 'Items over ~2 kg per piece in Phase 1', rw: 'Ibintu birenze ~2 kg kuri kimwe muri iki cyiciro' },
  prohib5: { en: 'Anything restricted by Rwandan import law', rw: 'Ikintu cyose kibujijwe n’amategeko y’u Rwanda' },

  // Terms
  termsTitle: { en: 'The promises we make', rw: 'Ibyo twiyemeza' },
  terms1t: { en: 'Delivery takes 2–4 weeks', rw: 'Ibyumweru 2–4' },
  terms1d: {
    en: 'From confirmed payment to your door. We consolidate weekly batches, ship by EMS, and clear customs in Kigali — updates at every step.',
    rw: 'Uhereye igihe wishyuriye kugeza bikugezeho. Twohereza buri cyumweru, tukamenyesha kuri buri ntambwe.',
  },
  terms2t: { en: 'Lost or damaged = reship or full refund', rw: 'Byabuze cyangwa byangiritse = gusubizwa byose' },
  terms2d: {
    en: 'Every shipment is tracked. If your item is lost or arrives damaged, we reship it or refund 100% of what you paid. Your choice.',
    rw: 'Buri paki irakurikiranwa. Ibyo watumije bibuze cyangwa byangiritse, turabisubiza cyangwa tukagusubiza amafaranga yose. Wowe uhitamo.',
  },
  terms3t: { en: 'If customs holds an item', rw: 'Igihe gasutamo ifashe igicuruzwa' },
  terms3d: {
    en: 'We handle clearance with RRA at no extra cost to you. If an item cannot be released, we refund you in full.',
    rw: 'Twe tubikurikirana kwa RRA nta kindi wishyura. Iyo kidashoboye gusohoka, tugusubiza amafaranga yose.',
  },
  termsLink: { en: 'Read the full terms (EN / RW)', rw: 'Soma amasezerano yose (EN / RW)' },

  // Footer
  footerTag: {
    en: 'CmartBridge Rwanda — a bridge between Korean stores and your door in Kigali.',
    rw: 'CmartBridge Rwanda — ikiraro hagati y’amaduka y’Ubukoreya n’umuryango wawe i Kigali.',
  },
  footerPhase: {
    en: 'Phase 1: Kigali only · WhatsApp & Instagram ordering · registered with RDB',
    rw: 'Icyiciro 1: Kigali gusa · gutumiza kuri WhatsApp na Instagram',
  },

  // Cart / product page / checkout / payment — not yet reviewed by a native speaker,
  // same caveat as the rest of this file.
  cartAria: { en: 'Cart', rw: 'Igikapu' },
  pdpBack: { en: '← Back to catalog', rw: '← Subira ku bicuruzwa' },
  pdpAddToCart: { en: 'Add to cart', rw: 'Shyira mu gikapu' },
  pdpAdded: { en: 'Added ✓', rw: 'Byashyizwemo ✓' },
  pdpBuyNow: { en: 'Buy now', rw: 'Gura nonaha' },
  pdpAsk: { en: 'Ask a question on WhatsApp', rw: 'Baza ikibazo kuri WhatsApp' },

  cartTitle: { en: 'Your cart', rw: 'Igikapu cyawe' },
  cartEmpty: { en: 'Your cart is empty.', rw: 'Igikapu cyawe kirimo ubusa.' },
  cartBrowse: { en: 'Browse the catalog', rw: 'Reba ibicuruzwa' },
  cartRemove: { en: 'Remove', rw: 'Kuraho' },
  cartSubtotal: { en: 'Subtotal', rw: 'Igiteranyo' },
  cartCheckout: { en: 'Checkout', rw: 'Kwishyura' },
  cartFxNote: {
    en: 'The final price is confirmed at payment — the exchange rate can shift slightly between browsing and checkout.',
    rw: 'Igiciro nyacyo cyemezwa igihe cyo kwishyura — igiciro cy’ivunjisha gishobora guhinduka gato.',
  },

  coTitle: { en: 'Checkout', rw: 'Kwishyura' },
  coName: { en: 'Your name', rw: 'Izina ryawe' },
  coPhone: { en: 'Phone number', rw: 'Nimero ya telefoni' },
  coPhoneHint: {
    en: 'MTN number for MoMo payment (e.g. 078xxxxxxx).',
    rw: 'Nimero ya MTN yo kwishyura na MoMo (urugero 078xxxxxxx).',
  },
  coNote: { en: 'Delivery note (optional)', rw: 'Ubutumwa ku gutanga (bidasabwa)' },
  coPayMethod: { en: 'Payment method', rw: 'Uburyo bwo kwishyura' },
  coPayMomo: { en: 'Pay now with MTN MoMo', rw: 'Ishyura ubu na MTN MoMo' },
  coPayMomoSub: {
    en: 'Instant — you’ll get a payment prompt on your phone.',
    rw: 'Ako kanya — uzabona ubutumwa bwo kwishyura kuri telefoni yawe.',
  },
  coPayManual: { en: 'Airtel Money / bank transfer', rw: 'Airtel Money / banki' },
  coPayManualSub: {
    en: 'Confirm your order on WhatsApp, then pay and send a screenshot.',
    rw: 'Emeza itumiza kuri WhatsApp, hanyuma wishyure wohereze ifoto.',
  },
  coSubmitMomo: { en: 'Pay with MTN MoMo', rw: 'Ishyura na MTN MoMo' },
  coSubmitManual: { en: 'Confirm order on WhatsApp', rw: 'Emeza itumiza kuri WhatsApp' },

  payPending: {
    en: 'Check your phone and approve the MTN MoMo payment prompt…',
    rw: 'Reba kuri telefoni yawe wemeze ubutumwa bwa MTN MoMo…',
  },
  payFailed: { en: 'Payment did not go through.', rw: 'Kwishyura ntibyakunze.' },
  payTimeout: { en: 'This is taking longer than usual.', rw: 'Ibi biratinda kurusha uko bisanzwe.' },
  payRetry: { en: 'Try again', rw: 'Ongera ugerageze' },
  payAlreadyPaid: {
    en: 'I already paid — notify CmartBridge',
    rw: 'Nishyuye — menyesha CmartBridge',
  },
  paySwitchManual: { en: 'Pay with Airtel/bank instead', rw: 'Ishyura na Airtel/banki ahubwo' },

  ocTitle: { en: 'Order confirmed', rw: 'Itumiza ryemejwe' },
  ocSendWhatsapp: {
    en: 'Send my order to CmartBridge on WhatsApp',
    rw: 'Ohereza itumiza kuri CmartBridge kuri WhatsApp',
  },
  ocNextSteps: {
    en: 'We’ll send you WhatsApp updates as your order moves: purchased, shipped, arrived, and delivered.',
    rw: 'Tuzakoherereza ubutumwa kuri WhatsApp uko itumiza rigenda: kiguzwe, cyoherejwe, kigeze, kigejejwe.',
  },
  ocRefLabel: { en: 'Reference', rw: 'Nimero y’itumiza' },
  ocFallback: {
    en: 'We couldn’t find this order — if you just paid, check WhatsApp or contact us.',
    rw: 'Ntitwabashije kubona iri tumiza — niba wamaze kwishyura, reba WhatsApp cyangwa utwandikire.',
  },

  notFoundTitle: { en: 'Page not found', rw: 'Iyi paji ntiboneka' },
  notFoundBack: { en: 'Back to home', rw: 'Subira ahabanza' },
}
