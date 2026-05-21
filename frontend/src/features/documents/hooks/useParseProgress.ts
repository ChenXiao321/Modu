import { useEffect, useRef, useState, useCallback } from 'react'
import { getParseStatus } from '../api'
import type { ParseStatusResponse } from '../types'

interface UseParseProgressOptions {
  documentId: string
  interval?: number
}

const MAX_CONSECUTIVE_ERRORS = 5

export function useParseProgress({ documentId, interval = 2000 }: UseParseProgressOptions) {
  const [status, setStatus] = useState<ParseStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorCount, setErrorCount] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    setErrorCount(0)
    setLoading(true)
    const poll = async () => {
      try {
        const res = await getParseStatus(documentId)
        setStatus(res)
        setErrorCount(0)
        if (res.status === 'completed' || res.status === 'failed') {
          stopPolling()
          setLoading(false)
        }
      } catch {
        setErrorCount((prev) => {
          const next = prev + 1
          if (next >= MAX_CONSECUTIVE_ERRORS) {
            stopPolling()
            setLoading(false)
          }
          return next
        })
      }
    }
    poll()
    timerRef.current = setInterval(poll, interval)
  }, [documentId, interval, stopPolling])

  // Reset when documentId changes
  useEffect(() => {
    setStatus(null)
    setErrorCount(0)
    startPolling()
    return () => stopPolling()
  }, [documentId, startPolling, stopPolling])

  return { status, loading, errorCount, startPolling, stopPolling }
}
