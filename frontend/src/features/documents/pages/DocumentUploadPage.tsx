import React from 'react'
import { Card, Typography, Space } from 'antd'
import DocumentUploader from '../components/DocumentUploader'

const { Title, Text } = Typography

const DocumentUploadPage: React.FC = () => {
  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2}>文档上传</Title>
          <Text type="secondary">
            上传芯片手册、需求规格等上游文档，平台将自动解析并提取结构化需求。
          </Text>
        </div>
        <Card title="上传文件" bordered>
          <DocumentUploader />
        </Card>
      </Space>
    </div>
  )
}

export default DocumentUploadPage
