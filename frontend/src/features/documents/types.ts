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

export interface ParseTriggerResponse {
  documentId: string
  parseTaskId: string
  status: string
}

export interface ParseStatusResponse {
  documentId: string
  status: string
  progressPercent: number
  message?: string
}

export interface RequirementTreeNode {
  id: string
  requirementId: string
  description: string
  chapter?: string
  asilLevel?: string
  children: RequirementTreeNode[]
}

export interface SafetyParameter {
  id: string
  parameterId: string
  name: string
  value: string
  unit?: string
  tolerance?: string
  chapter?: string
  sourcePage?: number
}

export interface OcrField {
  id: string
  fieldId: string
  extractedText: string
  normalizedValue?: string
  confidence: number
  fieldType?: string
  sourcePage?: number
  reviewStatus: string
  reviewedBy?: string
  reviewedAt?: string
}

export interface DocumentListItem {
  documentId: string
  originalFilename: string
  fileType: string
  fileSizeBytes: number
  uploadStatus: string
  parseStatus?: string
  pipelineStatus?: string
  blockReason?: string
  createdAt?: string
}
