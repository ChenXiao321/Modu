import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Button, Spin, Alert, Space, Tabs } from 'antd'
import {
  ArrowLeftOutlined,
  SafetyOutlined,
  ApartmentOutlined,
  FileImageOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { getRequirements, getSafetyParameters, getOcrResults, confirmOcrField } from '../api'
import RequirementTree from '../components/RequirementTree'
import SafetyParameterTable from '../components/SafetyParameterTable'
import OcrResultTable from '../components/OcrResultTable'
import type { RequirementTreeNode, SafetyParameter, OcrField } from '../types'

const { Title, Text } = Typography

const RequirementViewerPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [requirements, setRequirements] = useState<RequirementTreeNode[]>([])
  const [safetyParameters, setSafetyParameters] = useState<SafetyParameter[]>([])
  const [ocrFields, setOcrFields] = useState<OcrField[]>([])
  const [pipelineStatus, setPipelineStatus] = useState<string>('ready')
  const [blockReason, setBlockReason] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmingFieldId, setConfirmingFieldId] = useState<string | null>(null)
  const [reviewerName, setReviewerName] = useState<string>('')

  useEffect(() => {
    if (!documentId) return
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [reqs, params, ocr] = await Promise.all([
          getRequirements(documentId),
          getSafetyParameters(documentId),
          getOcrResults(documentId),
        ])
        setRequirements(reqs)
        setSafetyParameters(params)
        setOcrFields(ocr.fields)
        setPipelineStatus(ocr.pipelineStatus)
        setBlockReason(ocr.blockReason)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [documentId])

  const handleConfirmField = async (fieldId: string) => {
    if (!documentId) return
    if (!reviewerName.trim()) {
      setError('请先输入复核人姓名')
      return
    }
    setConfirmingFieldId(fieldId)
    try {
      const result = await confirmOcrField(documentId, fieldId, reviewerName.trim())
      setOcrFields((prev) =>
        prev.map((f) =>
          f.fieldId === fieldId
            ? {
                ...f,
                reviewStatus: result.reviewStatus,
                reviewedBy: result.reviewedBy,
                reviewedAt: result.reviewedAt,
              }
            : f
        )
      )
      setPipelineStatus(result.pipelineStatus)
      setBlockReason(result.blockReason)
    } catch (e) {
      setError(e instanceof Error ? e.message : '确认失败')
    } finally {
      setConfirmingFieldId(null)
    }
  }

  const lowConfidenceCount = ocrFields.filter(
    (f) => f.confidence < 0.95 && f.reviewStatus !== 'confirmed'
  ).length

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
    {
      key: 'ocr',
      label: (
        <span>
          <FileImageOutlined />
          OCR 提取结果
          {ocrFields.length > 0 && (
            <span style={{ marginLeft: 8 }}>({ocrFields.length})</span>
          )}
          {lowConfidenceCount > 0 && (
            <span style={{ marginLeft: 4, color: '#ff4d4f', fontWeight: 700 }}>
              !{lowConfidenceCount}
            </span>
          )}
        </span>
      ),
      children: (
        <Card
          title={`OCR 提取字段列表${ocrFields.length > 0 ? `（共 ${ocrFields.length} 条）` : ''}`}
        >
          {ocrFields.length === 0 && !loading && (
            <Alert
              message="暂无 OCR 提取结果"
              description="该文档为非扫描件格式，或解析尚未完成。"
              type="info"
              showIcon
            />
          )}
          {ocrFields.length > 0 && (
            <OcrResultTable
              fields={ocrFields}
              pipelineBlocked={pipelineStatus === 'blocked'}
              onConfirm={handleConfirmField}
              confirmingFieldId={confirmingFieldId}
            />
          )}
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
          <Text type="secondary">文档 ID: {documentId}</Text>
        </div>

        {pipelineStatus === 'blocked' && (
          <Alert
            message="流水线已阻塞"
            description={blockReason || '存在未复核的低置信度 OCR 字段'}
            type="error"
            showIcon
            icon={<ExclamationCircleOutlined />}
            action={
              <Button size="small" danger onClick={() => {
                const ocrTab = document.querySelector('[data-node-key="ocr"]') as HTMLElement
                ocrTab?.click()
              }}>
                前往复核
              </Button>
            }
          />
        )}

        {ocrFields.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <span style={{ marginRight: 8 }}>复核人姓名:</span>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="请输入您的姓名"
              style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #d9d9d9' }}
            />
          </div>
        )}

        {(pipelineStatus === 'ready' || pipelineStatus === 'in_design' || pipelineStatus === 'design_reviewed') && (
          <Alert
            message="流水线状态正常"
            description="文档解析已完成，可以进入方案设计阶段。"
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            action={
              <Space>
                <Button
                  type="primary"
                  icon={<FileTextOutlined />}
                  onClick={() => navigate(`/documents/${documentId}/design`)}
                >
                  进入方案设计
                </Button>
                {(pipelineStatus === 'in_design' || pipelineStatus === 'design_reviewed') && (
                  <Button
                    icon={<EyeOutlined />}
                    onClick={() => documentId && navigate(`/documents/${documentId}/design-review`)}
                  >
                    进入设计审查
                  </Button>
                )}
              </Space>
            }
          />
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在加载解析结果...</div>
          </div>
        )}

        {error && (
          <Alert message="加载失败" description={error} type="error" showIcon />
        )}

        {!loading && !error && (
          <Tabs defaultActiveKey="requirements" items={tabItems} />
        )}
      </Space>
    </div>
  )
}

export default RequirementViewerPage
