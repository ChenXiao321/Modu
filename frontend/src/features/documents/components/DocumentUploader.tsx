import React, { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Button, Alert, Space, message } from 'antd'
import { InboxOutlined, PauseCircleOutlined, PlayCircleOutlined, FileSearchOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { MAX_UPLOAD_SIZE_MB } from '../../../config'
import { useChunkedUpload } from '../../../hooks/useChunkedUpload'
import { triggerParse } from '../api'
import UploadProgress from './UploadProgress'

const { Dragger } = Upload

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'text/plain',
  'image/jpeg',
  'image/png',
  'image/tiff',
]

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.pptx', '.ppt', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.tif']

const DocumentUploader: React.FC = () => {
  const navigate = useNavigate()
  const { state, uploadFile, pauseUpload, resumeUpload } = useChunkedUpload()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [parseTriggered, setParseTriggered] = useState(false)

  const [parseError, setParseError] = useState<string | null>(null)

  useEffect(() => {
    if (state.status === 'completed' && state.documentId && !parseTriggered) {
      setParseTriggered(true)
      triggerParse(state.documentId).catch((e) => {
        const msg = e instanceof Error ? e.message : '解析任务触发失败'
        setParseError(msg)
      })
    }
  }, [state.status, state.documentId, parseTriggered])

  const beforeUpload = useCallback((file: UploadFile) => {
    const rawFile = file as unknown as File

    if (rawFile.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      message.error(`文件大小超过 ${MAX_UPLOAD_SIZE_MB}MB 限制`)
      return Upload.LIST_IGNORE
    }

    const ext = rawFile.name.slice(rawFile.name.lastIndexOf('.')).toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      message.error('不支持的文件格式')
      return Upload.LIST_IGNORE
    }

    if (rawFile.type && !ALLOWED_TYPES.includes(rawFile.type)) {
      // Allow if extension matches even if MIME type is unusual
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        message.error('不支持的文件格式')
        return Upload.LIST_IGNORE
      }
    }

    // Reset parse state for new file selection
    setParseTriggered(false)
    setParseError(null)
    setSelectedFile(rawFile)
    return false // Prevent default upload, we'll use chunked upload
  }, [])

  const handleUpload = useCallback(async () => {
    if (!selectedFile) {
      message.warning('请先选择文件')
      return
    }
    await uploadFile(selectedFile)
  }, [selectedFile, uploadFile])

  const handleRemove = useCallback(() => {
    setSelectedFile(null)
  }, [])

  return (
    <div style={{ width: '100%', maxWidth: 720 }}>
      <Dragger
        name="file"
        multiple={false}
        beforeUpload={beforeUpload}
        onRemove={handleRemove}
        fileList={selectedFile ? [{ uid: selectedFile.name, name: selectedFile.name, status: 'done', size: selectedFile.size }] : []}
        disabled={state.status === 'uploading'}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">
          支持 PDF、Word、Excel、PPT、TXT、图片格式，单文件最大 {MAX_UPLOAD_SIZE_MB}MB
        </p>
      </Dragger>

      {selectedFile && state.status !== 'idle' && (
        <div style={{ marginTop: 24 }}>
          <UploadProgress
            progress={state.progress}
            speed={state.speed}
            remainingTime={state.remainingTime}
            status={state.status}
          />
        </div>
      )}

      {state.error && (
        <Alert
          message="上传失败"
          description={state.error}
          type="error"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}

      {state.status === 'completed' && state.documentId && (
        <Alert
          message="上传成功，解析任务已触发"
          description={`文档 ID: ${state.documentId}`}
          type="success"
          showIcon
          style={{ marginTop: 16 }}
          action={
            <Button size="small" icon={<FileSearchOutlined />} onClick={() => navigate('/documents')}>
              查看文档列表
            </Button>
          }
        />
      )}

      {parseError && (
        <Alert
          message="解析任务触发失败"
          description={parseError}
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}

      <Space style={{ marginTop: 24 }}>
        <Button
          type="primary"
          onClick={handleUpload}
          disabled={!selectedFile || state.status === 'uploading'}
          loading={state.status === 'uploading'}
        >
          开始上传
        </Button>
        {state.status === 'uploading' && (
          <Button icon={<PauseCircleOutlined />} onClick={pauseUpload}>
            暂停
          </Button>
        )}
        {state.status === 'paused' && (
          <Button icon={<PlayCircleOutlined />} onClick={resumeUpload}>
            继续
          </Button>
        )}
      </Space>
    </div>
  )
}

export default DocumentUploader
