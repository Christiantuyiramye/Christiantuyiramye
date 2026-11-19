// Contact points — REPLACE PLACEHOLDERS BEFORE LAUNCH.
export const SITE = {
  // Kigali operations WhatsApp Business number, international format, digits only.
  whatsappNumber: '250780000000', // TODO: real number
  instagram: 'cmartbridge.rw', // TODO: real handle
  email: 'hello@cmartbridge.rw', // TODO: real inbox
  deliveryWindow: '2–4', // weeks, quoted everywhere
}

export function waLink(message) {
  return `https://wa.me/${SITE.whatsappNumber}?text=${encodeURIComponent(message)}`
}
