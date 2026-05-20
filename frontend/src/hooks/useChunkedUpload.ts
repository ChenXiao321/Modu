import { useState, useCallback, useRef } from 'react'
import { MAX_UPLOAD_SIZE_MB, CHUNK_SIZE_MB, MAX_CONCURRENT_CHUNKS, MAX_RETRY_COUNT } from '../config'
import { initUpload, uploadChunk, completeUpload } from '../features/documents/api'

interface UploadState {
  status: 'idle' | 'uploading' | 'paused' | 'completed' | 'error'
  progress: number
  speed: number // bytes per second
  remainingTime: number // seconds
  documentId: string | null
  error: string | null
}

interface UseChunkedUploadReturn {
  state: UploadState
  uploadFile: (file: File) => Promise<void>
  pauseUpload: () => void
  resumeUpload: () => void
}

const CHUNK_SIZE = CHUNK_SIZE_MB * 1024 * 1024

// Simple MD5-like checksum without external lib for MVP
async function simpleChecksum(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer()
  const bytes = new Uint8Array(buf)
  let hash = 0
  for (let i = 0; i < bytes.length; i++) {
    hash = (hash * 31 + bytes[i]) & 0xffffffff
  }
  return hash.toString(16).padStart(8, '0')
}

function loadUploadedChunks(documentId: string): Set<number> {
  const raw = sessionStorage.getItem(`upload_chunks_${documentId}`)
  if (!raw) return new Set()
  return new Set(JSON.parse(raw))
}

function saveUploadedChunks(documentId: string, chunks: Set<number>) {
  sessionStorage.setItem(`upload_chunks_${documentId}`, JSON.stringify([...chunks]))
}

function clearUploadedChunks(documentId: string) {
  sessionStorage.removeItem(`upload_chunks_${documentId}`)
}

export function useChunkedUpload(): UseChunkedUploadReturn {
  const [state, setState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    speed: 0,
    remainingTime: 0,
    documentId: null,
    error: null,
  })

  const abortRef = useRef(false)
  const pausedRef = useRef(false)
  const fileRef = useRef<File | null>(null)
  const uploadInfoRef = useRef<{ documentId: string; totalChunks: number } | null>(null)

  const uploadChunks = useCallback(async (
    file: File,
    documentId: string,
    totalChunks: number
  ) => {
    const uploaded = loadUploadedChunks(documentId)
    const startTime = Date.now()
    let uploadedBytes = uploaded.size * CHUNK_SIZE

    const chunksToUpload: number[] = []
    for (let i = 0; i < totalChunks; i++) {
      if (!uploaded.has(i)) chunksToUpload.push(i)
    }

    const runChunk = async (index: number): Promise<void> => {
      if (abortRef.current) throw new Error('上传已取消')
      while (pausedRef.current) {
        await new Promise((r) => setTimeout(r, 500))
        if (abortRef.current) throw new Error('上传已取消')
      }

      const start = index * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const blob = file.slice(start, end)
      const checksum = await simpleChecksum(blob)

      let lastError: Error | null = null
      for (let attempt = 0; attempt < MAX_RETRY_COUNT; attempt++) {
        try {
          await uploadChunk(documentId, index, blob, checksum)
          uploaded.add(index)
          saveUploadedChunks(documentId, uploaded)
          uploadedBytes += blob.size

          const elapsedSec = (Date.now() - startTime) / 1000
          const speed = elapsedSec > 0 ? uploadedBytes / elapsedSec : 0
          const remainingBytes = file.size - uploadedBytes
          const remainingTime = speed > 0 ? remainingBytes / speed : 0
          const progress = Math.round((uploaded.size / totalChunks) * 100)

          setState((s) => ({
            ...s,
            progress,
            speed,
            remainingTime,
          }))
          return
        } catch (err) {
          lastError = err as Error
          await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)))
        }
      }
      throw lastError || new Error(`分片 ${index} 上传失败`)
    }

    // Process chunks with concurrency limit
    const executing: Promise<void>[] = []
    for (const index of chunksToUpload) {
      const p = runChunk(index)
      executing.push(p)
      if (executing.length >= MAX_CONCURRENT_CHUNKS) {
        await Promise.race(executing)
        executing.splice(
          0,
          executing.length,
          ...executing.filter((ex) =>
            ex.then(() => false).catch(() => false) !== undefined
          )
        )
      }
    }
    await Promise.all(executing)
  }, [])

  const uploadFile = useCallback(async (file: File) => {
    // Pre-validation
    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      setState((s) => ({ ...s, status: 'error', error: `文件大小超过 ${MAX_UPLOAD_SIZE_MB}MB 限制` }))
      return
    }

    setState({
      status: 'uploading',
      progress: 0,
      speed: 0,
      remainingTime: 0,
      documentId: null,
      error: null,
    })
    abortRef.current = false
    pausedRef.current = false
    fileRef.current = file

    try {
      const initRes = await initUpload(file.name, file.size, file.type || 'application/octet-stream')
      const { documentId, maxChunks } = initRes
      uploadInfoRef.current = { documentId, totalChunks: maxChunks }

      setState((s) => ({ ...s, documentId }))

      await uploadChunks(file, documentId, maxChunks)

      // Compute file SHA-256
      const fileBuf = await file.arrayBuffer()
      const hashBuf = await crypto.subtle.digest('SHA-256', fileBuf)
      const sha256 = Array.from(new Uint8Array(hashBuf))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')

      await completeUpload(documentId, maxChunks, sha256)
      clearUploadedChunks(documentId)

      setState((s) => ({ ...s, status: 'completed', progress: 100 }))
    } catch (err) {
      const msg = err instanceof Error ? err.message : '上传失败'
      setState((s) => ({ ...s, status: 'error', error: msg }))
    }
  }, [uploadChunks])

  const pauseUpload = useCallback(() => {
    pausedRef.current = true
    setState((s) => ({ ...s, status: 'paused' }))
  }, [])

  const resumeUpload = useCallback(async () => {
    pausedRef.current = false
    setState((s) => ({ ...s, status: 'uploading' }))
    const file = fileRef.current
    const info = uploadInfoRef.current
    if (file && info) {
      try {
        await uploadChunks(file, info.documentId, info.totalChunks)
        const fileBuf = await file.arrayBuffer()
        const hashBuf = await crypto.subtle.digest('SHA-256', fileBuf)
        const sha256 = Array.from(new Uint8Array(hashBuf))
          .map((b) => b.toString(16).padStart(2, '0'))
          .join('')
        await completeUpload(info.documentId, info.totalChunks, sha256)
        clearUploadedChunks(info.documentId)
        setState((s) => ({ ...s, status: 'completed', progress: 100 }))
      } catch (err) {
        const msg = err instanceof Error ? err.message : '上传失败'
        setState((s) => ({ ...s, status: 'error', error: msg }))
      }
    }
  }, [uploadChunks])

  return { state, uploadFile, pauseUpload, resumeUpload }
}
