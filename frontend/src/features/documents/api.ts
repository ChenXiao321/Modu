import api from '../../api/axios'
import {
  DocumentListItem,
  DocumentStatus,
  ParseStatusResponse,
  ParseTriggerResponse,
  RequirementTreeNode,
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

  await api.post('/documents/upload/chunk', formData)
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
  return res.data.data
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatus> {
  const res = await api.get(`/documents/${documentId}/status`)
  return res.data.data
}

export async function triggerParse(documentId: string): Promise<ParseTriggerResponse> {
  const res = await api.post(`/documents/${documentId}/parse`)
  return res.data.data
}

export async function getParseStatus(documentId: string): Promise<ParseStatusResponse> {
  const res = await api.get(`/documents/${documentId}/parse/status`)
  return res.data.data
}

export async function getRequirements(documentId: string): Promise<RequirementTreeNode[]> {
  const res = await api.get(`/documents/${documentId}/requirements`)
  return res.data.data.requirements
}

export async function getSafetyParameters(documentId: string): Promise<SafetyParameter[]> {
  const res = await api.get(`/documents/${documentId}/safety-parameters`)
  return res.data.data.parameters
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await api.get('/documents')
  return res.data.data.items
}
