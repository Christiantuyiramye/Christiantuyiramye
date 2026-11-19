// Drives the MTN MoMo checkout call + status polling against the backend
// (server/routes.js). The server recomputes and returns the authoritative amount —
// this hook only ever displays/polls what the server said, never re-derives it.
import { useCallback, useEffect, useRef, useState } from 'react'

const SESSION_KEY = 'cmartbridge_momo_pending_v1'
const POLL_INTERVAL_MS = 4000
const POLL_TIMEOUT_MS = 120000

function readPending() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY))
  } catch {
    return null
  }
}

function writePending(data) {
  try {
    if (data) sessionStorage.setItem(SESSION_KEY, JSON.stringify(data))
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // sessionStorage unavailable — an in-flight payment just won't survive a refresh
  }
}

export function useMomoCheckout() {
  // idle | pending | success | failed | timeout | error
  const [state, setState] = useState('idle')
  const [order, setOrder] = useState(null)
  const [error, setError] = useState(null)
  const pollTimer = useRef(null)
  const pollDeadline = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollTimer.current) clearTimeout(pollTimer.current)
    pollTimer.current = null
  }, [])

  const poll = useCallback((referenceId) => {
    pollDeadline.current = Date.now() + POLL_TIMEOUT_MS

    const tick = async () => {
      try {
        const res = await fetch(`/api/momo/status/${referenceId}`)
        const data = await res.json()
        if (data.status === 'SUCCESSFUL') {
          setState('success')
          writePending(null)
          return
        }
        if (data.status === 'FAILED') {
          setState('failed')
          setError(data.reason || null)
          writePending(null)
          return
        }
      } catch {
        // transient network error — keep polling until the deadline
      }
      if (Date.now() >= pollDeadline.current) {
        setState('timeout')
        return
      }
      pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS)
    }

    tick()
  }, [])

  const pay = useCallback(
    async ({ cart, phone, name, note }) => {
      setState('pending')
      setError(null)
      try {
        const res = await fetch('/api/momo/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cart, phone, name, note }),
        })
        const data = await res.json()
        if (!res.ok) {
          setState('error')
          setError(data.error || 'request_failed')
          return
        }
        setOrder(data)
        writePending({ ...data, createdAt: Date.now() })
        poll(data.referenceId)
      } catch {
        setState('error')
        setError('network_error')
      }
    },
    [poll],
  )

  const reset = useCallback(() => {
    stopPolling()
    setState('idle')
    setOrder(null)
    setError(null)
    writePending(null)
  }, [stopPolling])

  useEffect(() => {
    const pending = readPending()
    if (pending?.referenceId) {
      setOrder(pending)
      setState('pending')
      poll(pending.referenceId)
    }
    return stopPolling
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { state, order, error, pay, reset }
}
