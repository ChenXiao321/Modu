export interface UploadInitResponse {
  documentId: string
  chunkSize: number
  maxChunks: number
}

export interface DocumentStatus {
  documentId: string
  status: string
  progressPercent: number
  parseTaskId?: string
  originalFilename?: string
}

export interface UploadChunkResult {
  documentId: string
  chunkIndex: number
  received: boolean
  progressPercent: number
}

export interface UploadCompleteResponse {
  documentId: string
  status: string
  storagePath: string
  sha256: string
}
