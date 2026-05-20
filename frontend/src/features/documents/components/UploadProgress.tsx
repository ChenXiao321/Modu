import React from 'react'
import { Progress, Typography, Space } from 'antd'

const { Text } = Typography

interface UploadProgressProps {
  progress: number
  speed: number
  remainingTime: number
  status: string
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec === 0) return '-'
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`
  return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`
}

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds <= 0) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) return `${mins}分 ${secs}秒`
  return `${secs}秒`
}

const UploadProgress: React.FC<UploadProgressProps> = ({
  progress,
  speed,
  remainingTime,
  status,
}) => {
  const statusMap: Record<string, 'normal' | 'success' | 'exception' | 'active'> = {
    idle: 'normal',
    uploading: 'active',
    paused: 'normal',
    completed: 'success',
    error: 'exception',
  }

  return (
    <div style={{ width: '100%', maxWidth: 600 }}>
      <Progress
        percent={progress}
        status={statusMap[status] || 'normal'}
        strokeWidth={12}
        showInfo
      />
      <Space size="large">
        <Text type="secondary">速度: {formatSpeed(speed)}</Text>
        <Text type="secondary">预计剩余: {formatTime(remainingTime)}</Text>
      </Space>
    </div>
  )
}

export default UploadProgress
