import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Tag, Typography, Space, Card, Alert } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import { listDocuments } from '../api'
import type { DocumentListItem } from '../types'

const { Title } = Typography

const DocumentListPage: React.FC = () => {
  const navigate = useNavigate()
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const items = await listDocuments()
      setDocuments(items)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  const columns = [
    {
      title: '文件名',
      dataIndex: 'originalFilename',
      key: 'originalFilename',
    },
    {
      title: '格式',
      dataIndex: 'fileType',
      key: 'fileType',
    },
    {
      title: '大小',
      dataIndex: 'fileSizeBytes',
      key: 'fileSizeBytes',
      render: (bytes: number) => `${(bytes / 1024 / 1024).toFixed(2)} MB`,
    },
    {
      title: '解析状态',
      dataIndex: 'parseStatus',
      key: 'parseStatus',
      render: (status: string | undefined) => {
        if (status === 'completed') return <Tag color="green">已完成</Tag>
        if (status === 'failed') return <Tag color="red">失败</Tag>
        if (status === 'running') return <Tag color="blue">解析中</Tag>
        if (status === 'pending') return <Tag color="orange">待解析</Tag>
        return <Tag>未开始</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: DocumentListItem) => (
        <Space>
          <Button
            type="link"
            onClick={() => navigate(`/documents/${record.documentId}/requirements`)}
            disabled={record.parseStatus !== 'completed'}
          >
            查看需求
          </Button>
          <Button
            type="link"
            onClick={() => navigate(`/documents/${record.documentId}/design`)}
            disabled={record.parseStatus !== 'completed'}
          >
            设计文档
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2}>文档管理</Title>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => navigate('/')}
          >
            上传新文档
          </Button>
        </div>
        {error && (
          <Alert
            message="加载失败"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <Card>
          <Table
            rowKey="documentId"
            dataSource={documents}
            columns={columns}
            loading={loading}
          />
        </Card>
      </Space>
    </div>
  )
}

export default DocumentListPage
