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

export interface DesignSection {
  content: string
  polarionTraceId: string
}

export interface DesignDocument {
  documentId: string
  status: string
  asilLevel?: string
  sections?: Record<string, DesignSection>
  errorMessage?: string
}

export type PipelineStatus =
  | 'ready'
  | 'blocked'
  | 'in_design'
  | 'design_reviewed'
  | 'pending'
  | 'failed'
  | 'completed'
  | 'generating'

export interface DocumentListItem {
  documentId: string
  originalFilename: string
  fileType: string
  fileSizeBytes: number
  uploadStatus: string
  parseStatus?: string
  pipelineStatus?: PipelineStatus
  blockReason?: string
  createdAt?: string
}

export interface DesignRevision {
  id: string
  sectionKey: string
  originalContent: string
  revisedContent: string
  author: string
  createdAt: string
}

export interface DesignRevisionWithDiff extends DesignRevision {
  diff: string
}

export interface ReviewComment {
  id: string
  sectionKey: string
  author: string
  commentText: string
  createdAt: string
  resolvedAt?: string
  resolvedBy?: string
}

export interface DesignReviewContext {
  documentId: string
  designDocument: DesignDocument
  requirements: RequirementTreeNode[]
  safetyParameters: SafetyParameter[]
  reviewComments: Record<string, ReviewComment[]>
  pendingCommentsCount: number
  pipelineStatus: PipelineStatus
}
