import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChunkedUpload } from './useChunkedUpload'

vi.mock('../features/documents/api', () => ({
  initUpload: vi.fn(),
  uploadChunk: vi.fn(),
  completeUpload: vi.fn(),
}))

vi.mock('../config', () => ({
  MAX_UPLOAD_SIZE_MB: 100,
  CHUNK_SIZE_MB: 1,
  MAX_CONCURRENT_CHUNKS: 3,
  MAX_RETRY_COUNT: 3,
}))

import { initUpload, uploadChunk, completeUpload } from '../features/documents/api'

describe('useChunkedUpload', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.mocked(initUpload).mockReset()
    vi.mocked(uploadChunk).mockReset()
    vi.mocked(completeUpload).mockReset()

    Object.defineProperty(globalThis, 'crypto', {
      value: {
        subtle: {
          digest: vi.fn(() => Promise.resolve(new ArrayBuffer(32))),
        },
      },
      writable: true,
      configurable: true,
    })

    // jsdom File.slice() may return a Blob without arrayBuffer()
    if (!Blob.prototype.arrayBuffer) {
      Object.defineProperty(Blob.prototype, 'arrayBuffer', {
        value: function (this: Blob) {
          return new Promise<ArrayBuffer>((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve(reader.result as ArrayBuffer)
            reader.readAsArrayBuffer(this)
          })
        },
      })
    }
  })

  const CHUNK_SIZE = 1 * 1024 * 1024

  function createFile(sizeBytes: number): File {
    return new File([new ArrayBuffer(sizeBytes)], 'test.pdf', { type: 'application/pdf' })
  }

  it('should reject files larger than MAX_UPLOAD_SIZE_MB', async () => {
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 1,
    })

    const { result } = renderHook(() => useChunkedUpload())
    const oversizedFile = createFile(101 * 1024 * 1024)

    await act(async () => {
      await result.current.uploadFile(oversizedFile)
    })

    expect(result.current.state.status).toBe('error')
    expect(result.current.state.error).toContain('超过')
    expect(initUpload).not.toHaveBeenCalled()
  })

  it('should initialize upload and complete all chunks', async () => {
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 2,
    })
    vi.mocked(uploadChunk).mockResolvedValue(undefined)
    vi.mocked(completeUpload).mockResolvedValue({ documentId: 'doc-1', status: 'completed', storagePath: '/tmp/test', sha256: 'abc123' })

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(CHUNK_SIZE + 100)

    await act(async () => {
      await result.current.uploadFile(file)
    })

    expect(initUpload).toHaveBeenCalledWith('test.pdf', file.size, 'application/pdf')
    expect(uploadChunk).toHaveBeenCalledTimes(2)
    expect(completeUpload).toHaveBeenCalledWith('doc-1', 2, expect.any(String))
    expect(result.current.state.status).toBe('completed')
    expect(result.current.state.progress).toBe(100)
    expect(sessionStorage.getItem('upload_chunks_doc-1')).toBeNull()
  })

  it('should retry failed chunks up to MAX_RETRY_COUNT then error', async () => {
    vi.useFakeTimers()
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 1,
    })
    vi.mocked(uploadChunk).mockRejectedValue(new Error('network error'))

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(100)

    act(() => {
      result.current.uploadFile(file)
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(7000)
    })

    expect(uploadChunk).toHaveBeenCalledTimes(3)
    expect(result.current.state.status).toBe('error')
    vi.useRealTimers()
  })

  it('should resume upload from sessionStorage checkpoints', async () => {
    sessionStorage.setItem('upload_chunks_doc-1', JSON.stringify([0]))

    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 3,
    })
    vi.mocked(uploadChunk).mockResolvedValue(undefined)
    vi.mocked(completeUpload).mockResolvedValue({ documentId: 'doc-1', status: 'completed', storagePath: '/tmp/test', sha256: 'abc123' })

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(3 * CHUNK_SIZE)

    await act(async () => {
      await result.current.uploadFile(file)
    })

    expect(uploadChunk).toHaveBeenCalledTimes(2)
    expect(completeUpload).toHaveBeenCalled()
  })

  it('should pause and resume upload', async () => {
    vi.useFakeTimers()
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 1,
    })

    let resolveChunk: (() => void) | null = null
    vi.mocked(uploadChunk).mockImplementation(() => {
      return new Promise<void>((resolve) => {
        resolveChunk = resolve
      })
    })
    vi.mocked(completeUpload).mockResolvedValue({ documentId: 'doc-1', status: 'completed', storagePath: '/tmp/test', sha256: 'abc123' })

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(100)

    act(() => {
      result.current.uploadFile(file)
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
    })
    expect(result.current.state.status).toBe('uploading')

    act(() => {
      result.current.pauseUpload()
    })
    expect(result.current.state.status).toBe('paused')

    act(() => {
      result.current.resumeUpload()
    })
    expect(result.current.state.status).toBe('uploading')

    await act(async () => {
      resolveChunk?.()
      await vi.advanceTimersByTimeAsync(2000)
    })

    expect(result.current.state.status).toBe('completed')
    vi.useRealTimers()
  })

  it('should calculate progress correctly during upload', async () => {
    vi.useFakeTimers()
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 2,
    })

    const resolvers: Array<() => void> = []
    vi.mocked(uploadChunk).mockImplementation(() => {
      return new Promise<void>((resolve) => {
        resolvers.push(resolve)
      })
    })
    vi.mocked(completeUpload).mockResolvedValue({ documentId: 'doc-1', status: 'completed', storagePath: '/tmp/test', sha256: 'abc123' })

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(2 * CHUNK_SIZE)

    act(() => {
      result.current.uploadFile(file)
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
    })
    expect(result.current.state.progress).toBe(0)

    await act(async () => {
      resolvers[0]?.()
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(result.current.state.progress).toBe(50)

    await act(async () => {
      resolvers[1]?.()
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(result.current.state.progress).toBe(100)
    vi.useRealTimers()
  })

  it('should set error status when final completeUpload fails', async () => {
    vi.mocked(initUpload).mockResolvedValue({
      documentId: 'doc-1',
      chunkSize: CHUNK_SIZE,
      maxChunks: 1,
    })
    vi.mocked(uploadChunk).mockResolvedValue(undefined)
    vi.mocked(completeUpload).mockRejectedValue(new Error('merge failed'))

    const { result } = renderHook(() => useChunkedUpload())
    const file = createFile(100)

    await act(async () => {
      await result.current.uploadFile(file)
    })

    expect(result.current.state.status).toBe('error')
    expect(result.current.state.error).toContain('merge failed')
  })
})
