import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Typography,
  Button,
  Spin,
  Alert,
  Space,
  Tag,
  Descriptions,
  Divider,
} from 'antd'
import {
  ArrowLeftOutlined,
  FileTextOutlined,
  ReloadOutlined,
  BookOutlined,
  ClusterOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  BugOutlined,
  SafetyOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { getDesignDocument, triggerDesignDocument } from '../api'
import type { DesignDocument, DesignSection } from '../types'

const { Title, Text, Paragraph } = Typography

const sectionConfig: Record<
  string,
  { label: string; icon: React.ReactNode }
> = {
  overview: { label: '概述', icon: <FileTextOutlined /> },
  references: { label: '引用文档', icon: <BookOutlined /> },
  system_architecture: { label: '系统架构', icon: <ClusterOutlined /> },
  interface_definition: { label: '接口定义', icon: <ApiOutlined /> },
  dynamic_behavior: { label: '动态行为', icon: <ThunderboltOutlined /> },
  resource_consumption: { label: '资源消耗估算', icon: <ExperimentOutlined /> },
  error_handling: { label: '错误处理策略', icon: <BugOutlined /> },
  test_strategy: { label: '测试策略', icon: <SafetyOutlined /> },
}

const SectionCard: React.FC<{ sectionKey: string; section: DesignSection }> = ({
  sectionKey,
  section,
}) => {
  const config = sectionConfig[sectionKey] || { label: sectionKey, icon: null }
  return (
    <Card
      title={
        <Space>
          {config.icon}
          <span>{config.label}</span>
        </Space>
      }
      style={{ marginBottom: 16 }}
      extra={
        <Tag color="blue">Polarion: {section.polarionTraceId || '-'}</Tag>
      }
    >
      <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
        {section.content || '（无内容）'}
      </Paragraph>
    </Card>
  )
}

const DesignDocumentPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [designDoc, setDesignDoc] = useState<DesignDocument | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDesignDoc = async () => {
    if (!documentId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getDesignDocument(documentId)
      setDesignDoc(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载设计文档失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!documentId) return
    fetchDesignDoc()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId])

  useEffect(() => {
    if (!documentId || designDoc?.status !== 'running') return
    let pollCount = 0
    const MAX_POLLS = 300
    let timeoutId: ReturnType<typeof setTimeout>

    const poll = async () => {
      try {
        const data = await getDesignDocument(documentId)
        setDesignDoc(data)
        pollCount++
        if (data.status === 'running' && pollCount < MAX_POLLS) {
          timeoutId = setTimeout(poll, 2000)
        } else if (data.status === 'running' && pollCount >= MAX_POLLS) {
          setError('设计文档生成超时，请稍后刷新页面或重新生成')
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : '轮询失败')
      }
    }

    timeoutId = setTimeout(poll, 2000)

    return () => clearTimeout(timeoutId)
  }, [documentId, designDoc?.status])

  const handleGenerate = async () => {
    if (!documentId) return
    setGenerating(true)
    setError(null)
    try {
      await triggerDesignDocument(documentId)
      await fetchDesignDoc()
    } catch (e) {
      setError(e instanceof Error ? e.message : '触发设计文档生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const statusTag = (status: string | undefined) => {
    switch (status) {
      case 'completed':
        return <Tag color="green">已完成</Tag>
      case 'running':
        return <Tag color="blue">生成中</Tag>
      case 'failed':
        return <Tag color="red">失败</Tag>
      case 'pending':
        return <Tag>待生成</Tag>
      default:
        return <Tag color="orange">未知状态: {status}</Tag>
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(`/documents/${documentId}/requirements`)}
            style={{ marginBottom: 16 }}
          >
            返回需求查看
          </Button>
          <Title level={2}>设计文档</Title>
          <Text type="secondary">文档 ID: {documentId}</Text>
        </div>

        {error && (
          <Alert message="错误" description={error} type="error" showIcon />
        )}

        <Card>
          <Descriptions title="设计文档状态" bordered>
            <Descriptions.Item label="生成状态">
              {statusTag(designDoc?.status)}
            </Descriptions.Item>
            <Descriptions.Item label="ASIL 等级">
              {designDoc?.asilLevel ? `ASIL-${designDoc.asilLevel}` : '-'}
            </Descriptions.Item>
          </Descriptions>
          <Divider />
          {designDoc?.status === 'pending' && (
            <Button
              type="primary"
              onClick={handleGenerate}
              loading={generating}
            >
              生成设计文档
            </Button>
          )}
          {(designDoc?.status === 'completed' || designDoc?.status === 'failed') && (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleGenerate}
              loading={generating}
            >
              重新生成
            </Button>
          )}
        </Card>

        {designDoc?.status === 'running' && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>AI 正在生成设计文档，请稍候...</div>
          </div>
        )}

        {designDoc?.status === 'failed' && designDoc.errorMessage && (
          <Alert
            message="生成失败"
            description={designDoc.errorMessage}
            type="error"
            showIcon
          />
        )}

        {designDoc?.status === 'completed' && designDoc.sections && (
          <div>
            {Object.entries(designDoc.sections).map(([key, section]) => (
              <SectionCard key={key} sectionKey={key} section={section} />
            ))}
          </div>
        )}

        {loading && !designDoc && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在加载...</div>
          </div>
        )}
      </Space>
    </div>
  )
}

export default DesignDocumentPage
