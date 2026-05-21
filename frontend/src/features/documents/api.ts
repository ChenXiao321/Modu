import api from '../../api/axios'
import {
  DocumentStatus,
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
