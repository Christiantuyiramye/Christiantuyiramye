// MTN MoMo Collections API client — token caching, Request to Pay, status check.
// Docs: https://momodeveloper.mtn.com
// Sandbox note: sandbox `requesttopay` only accepts currency=EUR; production
// (MOMO_TARGET_ENVIRONMENT=mtnrwanda) uses RWF. See .env.example.

const BASE_URL = process.env.MOMO_BASE_URL
const SUBSCRIPTION_KEY = process.env.MOMO_SUBSCRIPTION_KEY
const API_USER = process.env.MOMO_API_USER
const API_KEY = process.env.MOMO_API_KEY
const TARGET_ENVIRONMENT = process.env.MOMO_TARGET_ENVIRONMENT

let cachedToken = null // { accessToken, expiresAt }

async function getAccessToken() {
  if (cachedToken && Date.now() < cachedToken.expiresAt) {
    return cachedToken.accessToken
  }

  const basic = Buffer.from(`${API_USER}:${API_KEY}`).toString('base64')
  const res = await fetch(`${BASE_URL}/collection/token/`, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${basic}`,
      'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY,
    },
  })

  if (!res.ok) {
    throw new Error(`MoMo token request failed: ${res.status}`)
  }

  const data = await res.json()
  cachedToken = {
    accessToken: data.access_token,
    expiresAt: Date.now() + (Number(data.expires_in) - 60) * 1000, // refresh 60s early
  }
  return cachedToken.accessToken
}

export async function requestToPay({
  amount,
  currency,
  referenceId,
  payerMsisdn,
  payerMessage,
  payeeNote,
}) {
  const token = await getAccessToken()

  const res = await fetch(`${BASE_URL}/collection/v1_0/requesttopay`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'X-Reference-Id': referenceId,
      'X-Target-Environment': TARGET_ENVIRONMENT,
      'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      amount: String(amount),
      currency,
      externalId: referenceId,
      payer: { partyIdType: 'MSISDN', partyId: payerMsisdn },
      payerMessage,
      payeeNote,
    }),
  })

  if (res.status !== 202) {
    const body = await res.text().catch(() => '')
    throw new Error(`MoMo requestToPay failed: ${res.status} ${body}`)
  }
}

export async function getRequestToPayStatus(referenceId) {
  const token = await getAccessToken()

  const res = await fetch(`${BASE_URL}/collection/v1_0/requesttopay/${referenceId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'X-Target-Environment': TARGET_ENVIRONMENT,
      'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY,
    },
  })

  if (!res.ok) {
    throw new Error(`MoMo status check failed: ${res.status}`)
  }

  const data = await res.json()
  return { status: data.status, reason: data.reason }
}
