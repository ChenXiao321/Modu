import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Button, Spin, Alert, Space, Tabs } from 'antd'
import { ArrowLeftOutlined, SafetyOutlined, ApartmentOutlined } from '@ant-design/icons'
import { getRequirements, getSafetyParameters } from '../api'
import RequirementTree from '../components/RequirementTree'
import SafetyParameterTable from '../components/SafetyParameterTable'
import type { RequirementTreeNode, SafetyParameter } from '../types'

const { Title, Text } = Typography

const RequirementViewerPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [requirements, setRequirements] = useState<RequirementTreeNode[]>([])
  const [safetyParameters, setSafetyParameters] = useState<SafetyParameter[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!documentId) return
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [reqs, params] = await Promise.all([
          getRequirements(documentId),
          getSafetyParameters(documentId),
        ])
        setRequirements(reqs)
        setSafetyParameters(params)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [documentId])

  const tabItems = [
    {
      key: 'requirements',
      label: (
        <span>
          <ApartmentOutlined />
          功能需求
          {requirements.length > 0 && (
            <span style={{ marginLeft: 8 }}>({requirements.length})</span>
          )}
        </span>
      ),
      children: (
        <>
          {requirements.length === 0 && !loading && (
            <Alert
              message="暂无解析结果"
              description="该文档尚未完成解析或没有提取到结构化需求。"
              type="info"
              showIcon
            />
          )}
          {requirements.length > 0 && (
            <Card title={`共提取 ${requirements.length} 条顶级需求`}>
              <RequirementTree requirements={requirements} />
            </Card>
          )}
        </>
      ),
    },
    {
      key: 'safety',
      label: (
        <span>
          <SafetyOutlined />
          安全关键参数
          {safetyParameters.length > 0 && (
            <span style={{ marginLeft: 8 }}>({safetyParameters.length})</span>
          )}
        </span>
      ),
      children: (
        <Card title="安全关键参数列表">
          <SafetyParameterTable parameters={safetyParameters} />
        </Card>
      ),
    },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/documents')}
            style={{ marginBottom: 16 }}
          >
            返回文档列表
          </Button>
          <Title level={2}>结构化需求查看</Title>
          <Text type="secondary">
            文档 ID: {documentId}
          </Text>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在加载解析结果...</div>
          </div>
        )}

        {error && (
          <Alert
            message="加载失败"
            description={error}
            type="error"
            showIcon
          />
        )}

        {!loading && !error && (
          <Tabs defaultActiveKey="requirements" items={tabItems} />
        )}
      </Space>
    </div>
  )
}

export default RequirementViewerPage
