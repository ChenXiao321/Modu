import api from '../../api/axios'
import {
  DesignDocument,
  DesignReviewContext,
  DesignRevision,
  DesignRevisionWithDiff,
  DocumentListItem,
  DocumentStatus,
  OcrField,
  ParseStatusResponse,
  ParseTriggerResponse,
  QualityReport,
  RequirementTreeNode,
  ReviewComment,
  SafetyParameter,
  UploadCompleteResponse,
  UploadInitResponse,
} from './types'

export async function initUpload(
  filename: string,
  fileSizeBytes: number,
  fileType: string
): Promise<UploadInitResponse> {
  const res = await api.post('/documents/upload/init', {
    filename,
    file_size_bytes: fileSizeBytes,
    file_type: fileType,
  })
  checkSuccess(res)
  return res.data.data
}

export async function uploadChunk(
  documentId: string,
  chunkIndex: number,
  chunkBlob: Blob,
  checksum: string
): Promise<void> {
  const formData = new FormData()
  formData.append('document_id', documentId)
  formData.append('chunk_index', String(chunkIndex))
  formData.append('checksum', checksum)
  formData.append('chunk_data', chunkBlob, `chunk_${chunkIndex}`)

  const res = await api.post('/documents/upload/chunk', formData)
  checkSuccess(res)
}

export async function completeUpload(
  documentId: string,
  totalChunks: number,
  sha256: string
): Promise<UploadCompleteResponse> {
  const res = await api.post('/documents/upload/complete', {
    document_id: documentId,
    total_chunks: totalChunks,
    sha256,
  })
  checkSuccess(res)
  return res.data.data
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatus> {
  const res = await api.get(`/documents/${documentId}/status`)
  checkSuccess(res)
  return res.data.data
}

export async function triggerParse(documentId: string): Promise<ParseTriggerResponse> {
  const res = await api.post(`/documents/${documentId}/parse`)
  checkSuccess(res)
  return res.data.data
}

export async function getParseStatus(documentId: string): Promise<ParseStatusResponse> {
  const res = await api.get(`/documents/${documentId}/parse/status`)
  checkSuccess(res)
  return res.data.data
}

export async function getRequirements(documentId: string): Promise<RequirementTreeNode[]> {
  const res = await api.get(`/documents/${documentId}/requirements`)
  checkSuccess(res)
  return res.data.data.requirements
}

export async function getRequirementsQuality(documentId: string): Promise<QualityReport> {
  const res = await api.get(`/documents/${documentId}/requirements/quality`)
  checkSuccess(res)
  const data = res.data.data
  return {
    documentId: data.document_id,
    parseStatus: data.parse_status,
    qualitySummary: {
      total: data.quality_summary.total,
      errorCount: data.quality_summary.error_count,
      warningCount: data.quality_summary.warning_count,
      infoCount: data.quality_summary.info_count,
      pass: data.quality_summary.pass,
      errors: data.quality_summary.errors || [],
      warnings: data.quality_summary.warnings || [],
      infos: data.quality_summary.infos || [],
    },
    violations: data.violations || [],
  }
}

export async function getSafetyParameters(documentId: string): Promise<SafetyParameter[]> {
  const res = await api.get(`/documents/${documentId}/safety-parameters`)
  checkSuccess(res)
  return res.data.data.parameters
}

export async function getOcrResults(documentId: string): Promise<{ pipelineStatus: string; blockReason?: string; fields: OcrField[] }> {
  const res = await api.get(`/documents/${documentId}/ocr-results`)
  checkSuccess(res)
  return {
    pipelineStatus: res.data.data.pipeline_status,
    blockReason: res.data.data.block_reason,
    fields: res.data.data.fields,
  }
}

export async function confirmOcrField(
  documentId: string,
  fieldId: string,
  reviewerName: string
): Promise<{ fieldId: string; reviewStatus: string; reviewedBy: string; reviewedAt: string; pipelineStatus: string; allConfirmed: boolean; blockReason?: string }> {
  const res = await api.post(`/documents/${documentId}/ocr-fields/${fieldId}/confirm`, {
    reviewer_name: reviewerName,
  })
  checkSuccess(res)
  return res.data.data
}

export async function triggerDesignDocument(documentId: string): Promise<{ documentId: string; designTaskId: string; status: string }> {
  const res = await api.post(`/documents/${documentId}/design`)
  checkSuccess(res)
  return res.data.data
}

export async function getDesignDocument(documentId: string): Promise<DesignDocument> {
  const res = await api.get(`/documents/${documentId}/design`)
  checkSuccess(res)
  return res.data.data
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await api.get('/documents')
  checkSuccess(res)
  return res.data.data.items
}

// Design Review APIs (Story 2.2)

function checkSuccess(res: { data?: { success?: boolean; error?: { message?: string }; trace_id?: string } }): void {
  if (!res.data?.success) {
    const message = res.data?.error?.message || '请求失败'
    const traceId = res.data?.trace_id
    throw new Error(traceId ? `${message} (trace_id: ${traceId})` : message)
  }
}

function mapReviewComment(c: any): ReviewComment {
  return {
    id: c.id,
    sectionKey: c.section_key,
    author: c.author,
    commentText: c.comment_text,
    createdAt: c.created_at,
    resolvedAt: c.resolved_at,
    resolvedBy: c.resolved_by,
  }
}

function mapDesignRevision(r: any): DesignRevision {
  return {
    id: r.id ?? r.revision_id,
    sectionKey: r.section_key,
    originalContent: r.original_content,
    revisedContent: r.revised_content,
    author: r.author,
    createdAt: r.created_at,
  }
}

function mapDesignRevisionWithDiff(r: any): DesignRevisionWithDiff {
  return {
    ...mapDesignRevision(r),
    diff: r.diff,
  }
}

export async function getDesignReview(documentId: string): Promise<DesignReviewContext> {
  const res = await api.get(`/documents/${documentId}/design-review`)
  checkSuccess(res)
  const data = res.data.data
  return {
    documentId: data.document_id,
    designDocument: {
      documentId: data.design_document?.document_id ?? documentId,
      status: data.design_document?.status,
      asilLevel: data.design_document?.asil_level,
      sections: data.design_document?.sections
        ? Object.fromEntries(
            Object.entries(data.design_document.sections).map(([k, v]: [string, any]) => [
              k,
              { content: v.content, polarionTraceId: v.polarion_trace_id },
            ])
          )
        : undefined,
      errorMessage: data.design_document?.error_message,
    },
    requirements: data.requirements,
    safetyParameters: data.safety_parameters,
    reviewComments: Object.fromEntries(
      Object.entries(data.review_comments || {}).map(([key, comments]: [string, any]) => [
        key,
        comments.map(mapReviewComment),
      ])
    ),
    pendingCommentsCount: data.pending_comments_count,
    pipelineStatus: data.pipeline_status,
  }
}

export async function saveDesignRevision(
  documentId: string,
  sectionKey: string,
  revisedContent: string,
  author: string
): Promise<DesignRevision> {
  const res = await api.post(`/documents/${documentId}/design-revisions`, {
    section_key: sectionKey,
    revised_content: revisedContent,
    author,
  })
  checkSuccess(res)
  return mapDesignRevision(res.data.data)
}

export async function getDesignRevisions(
  documentId: string,
  sectionKey: string
): Promise<{ sectionKey: string; revisions: DesignRevisionWithDiff[] }> {
  const res = await api.get(`/documents/${documentId}/design-revisions`, {
    params: { section_key: sectionKey },
  })
  checkSuccess(res)
  const data = res.data.data
  return {
    sectionKey: data.section_key,
    revisions: data.revisions.map(mapDesignRevisionWithDiff),
  }
}

export async function addReviewComment(
  documentId: string,
  sectionKey: string,
  commentText: string,
  author: string
): Promise<ReviewComment> {
  const res = await api.post(`/documents/${documentId}/review-comments`, {
    section_key: sectionKey,
    comment_text: commentText,
    author,
  })
  checkSuccess(res)
  return mapReviewComment(res.data.data)
}

export async function getReviewComments(
  documentId: string,
  sectionKey: string
): Promise<{ sectionKey: string; comments: ReviewComment[] }> {
  const res = await api.get(`/documents/${documentId}/review-comments`, {
    params: { section_key: sectionKey },
  })
  checkSuccess(res)
  const data = res.data.data
  return {
    sectionKey: data.section_key,
    comments: data.comments.map(mapReviewComment),
  }
}

export async function resolveReviewComment(
  documentId: string,
  commentId: string,
  resolvedBy: string
): Promise<ReviewComment> {
  const res = await api.patch(`/documents/${documentId}/review-comments/${commentId}/resolve`, {
    resolved_by: resolvedBy,
  })
  checkSuccess(res)
  return mapReviewComment(res.data.data)
}

export async function submitDesignReview(documentId: string): Promise<{ documentId: string; pipelineStatus: string; submittedAt: string }> {
  const res = await api.post(`/documents/${documentId}/design-review/submit`)
  checkSuccess(res)
  const data = res.data.data
  return {
    documentId: data.document_id,
    pipelineStatus: data.pipeline_status,
    submittedAt: data.submitted_at,
  }
}

export async function rollbackToRevision(
  documentId: string,
  revisionId: string,
  author: string
): Promise<DesignRevision> {
  const res = await api.post(`/documents/${documentId}/design-revisions/${revisionId}/rollback`, {
    author,
  })
  checkSuccess(res)
  return mapDesignRevision(res.data.data)
}
