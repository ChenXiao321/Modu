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
  Divider,
  Splitter,
  Tabs,
  Badge,
} from 'antd'
import {
  ArrowLeftOutlined,
  FileTextOutlined,
  BookOutlined,
  ClusterOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  BugOutlined,
  SafetyOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import {
  getDesignReview,
  saveDesignRevision,
  getDesignRevisions,
  addReviewComment,
  getReviewComments,
  resolveReviewComment,
  submitDesignReview,
  rollbackToRevision,
} from '../api'
import RequirementTree from '../components/RequirementTree'
import SafetyParameterTable from '../components/SafetyParameterTable'
import SectionEditor from '../components/SectionEditor'
import RevisionHistory from '../components/RevisionHistory'
import ReviewCommentPanel from '../components/ReviewCommentPanel'
import type {
  DesignReviewContext,
  DesignSection,
  DesignRevisionWithDiff,
  ReviewComment,
} from '../types'

const { Title, Text } = Typography

const sectionConfig: Record<string, { label: string; icon: React.ReactNode }> = {
  overview: { label: '概述', icon: <FileTextOutlined /> },
  references: { label: '引用文档', icon: <BookOutlined /> },
  system_architecture: { label: '系统架构', icon: <ClusterOutlined /> },
  interface_definition: { label: '接口定义', icon: <ApiOutlined /> },
  dynamic_behavior: { label: '动态行为', icon: <ThunderboltOutlined /> },
  resource_consumption: { label: '资源消耗估算', icon: <ExperimentOutlined /> },
  error_handling: { label: '错误处理策略', icon: <BugOutlined /> },
  test_strategy: { label: '测试策略', icon: <SafetyOutlined /> },
}

const REVIEWER_NAME_KEY = 'modu_reviewer_name'

const DesignReviewPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [context, setContext] = useState<DesignReviewContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reviewerName, setReviewerName] = useState(() => {
    try {
      return localStorage.getItem(REVIEWER_NAME_KEY) || ''
    } catch {
      return ''
    }
  })

  // Revision history drawer state
  const [historyVisible, setHistoryVisible] = useState(false)
  const [historySectionKey, setHistorySectionKey] = useState('')
  const [historySectionLabel, setHistorySectionLabel] = useState('')
  const [revisions, setRevisions] = useState<DesignRevisionWithDiff[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  // Comments state per section
  const [commentsMap, setCommentsMap] = useState<Record<string, ReviewComment[]>>({})
  const [commentsLoading, setCommentsLoading] = useState<Record<string, boolean>>({})

  // Submit review loading
  const [submitting, setSubmitting] = useState(false)

  const fetchContext = async (signal?: AbortSignal) => {
    if (!documentId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getDesignReview(documentId)
      if (signal?.aborted) return
      setContext(data)
      // Pre-load comments for sections that have them
      const map: Record<string, ReviewComment[]> = {}
      Object.entries(data.reviewComments || {}).forEach(([key, list]) => {
        map[key] = list
      })
      setCommentsMap(map)
    } catch (e) {
      if (signal?.aborted) return
      setError(e instanceof Error ? e.message : '加载审查上下文失败')
    } finally {
      if (!signal?.aborted) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    if (!documentId) return
    const controller = new AbortController()
    fetchContext(controller.signal)
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId])

  const handleSaveRevision = async (sectionKey: string, newContent: string) => {
    if (!documentId || !reviewerName.trim()) {
      setError('请先输入您的姓名')
      return
    }
    try {
      await saveDesignRevision(documentId, sectionKey, newContent, reviewerName.trim())
      setError(null)
      await fetchContext()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存修订失败')
    }
  }

  const openRevisionHistory = async (sectionKey: string) => {
    if (!documentId) return
    setHistorySectionKey(sectionKey)
    setHistorySectionLabel(sectionConfig[sectionKey]?.label || sectionKey)
    setHistoryVisible(true)
    setHistoryLoading(true)
    try {
      const data = await getDesignRevisions(documentId, sectionKey)
      setRevisions(data.revisions)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载修订历史失败')
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleRollback = async (revisionId: string) => {
    if (!documentId || !reviewerName.trim()) {
      setError('请先输入您的姓名')
      return
    }
    try {
      await rollbackToRevision(documentId, revisionId, reviewerName.trim())
      setError(null)
      await fetchContext()
      // Refresh history drawer
      const data = await getDesignRevisions(documentId, historySectionKey)
      setRevisions(data.revisions)
    } catch (e) {
      setError(e instanceof Error ? e.message : '回退失败')
    }
  }

  const loadComments = async (sectionKey: string) => {
    if (!documentId) return
    setCommentsLoading((prev) => ({ ...prev, [sectionKey]: true }))
    try {
      const data = await getReviewComments(documentId, sectionKey)
      setCommentsMap((prev) => ({ ...prev, [sectionKey]: data.comments }))
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载评审意见失败')
    } finally {
      setCommentsLoading((prev) => ({ ...prev, [sectionKey]: false }))
    }
  }

  const handleAddComment = async (sectionKey: string, text: string) => {
    if (!documentId || !reviewerName.trim()) {
      setError('请先输入您的姓名')
      return
    }
    await addReviewComment(documentId, sectionKey, text, reviewerName.trim())
    await loadComments(sectionKey)
    await fetchContext()
  }

  const handleResolveComment = async (sectionKey: string, commentId: string) => {
    if (!documentId || !reviewerName.trim()) {
      setError('请先输入您的姓名')
      return
    }
    await resolveReviewComment(documentId, commentId, reviewerName.trim())
    await loadComments(sectionKey)
    await fetchContext()
  }

  const handleSubmitReview = async () => {
    if (!documentId) return
    setSubmitting(true)
    try {
      await submitDesignReview(documentId)
      setError(null)
      await fetchContext()
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交审查失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReviewerNameChange = (val: string) => {
    setReviewerName(val)
    try {
      localStorage.setItem(REVIEWER_NAME_KEY, val)
    } catch {
      // ignore localStorage errors (private mode, quota exceeded)
    }
  }

  const designDoc = context?.designDocument
  const sections = designDoc?.sections || {}
  const pendingCount = context?.pendingCommentsCount || 0
  const pipelineStatus = context?.pipelineStatus || 'ready'

  // Left panel tabs
  const leftTabItems = [
    {
      key: 'requirements',
      label: (
        <span>
          <ClusterOutlined /> 功能需求
          {context?.requirements && context.requirements.length > 0 && (
            <span style={{ marginLeft: 8 }}>({context.requirements.length})</span>
          )}
        </span>
      ),
      children: (
        <Card title="结构化需求">
          {context?.requirements && context.requirements.length > 0 ? (
            <RequirementTree requirements={context.requirements} />
          ) : (
            <Alert message="暂无需求数据" type="info" showIcon />
          )}
        </Card>
      ),
    },
    {
      key: 'safety',
      label: (
        <span>
          <SafetyOutlined /> 安全关键参数
          {context?.safetyParameters && context.safetyParameters.length > 0 && (
            <span style={{ marginLeft: 8 }}>({context.safetyParameters.length})</span>
          )}
        </span>
      ),
      children: (
        <Card title="安全关键参数列表">
          {context?.safetyParameters && context.safetyParameters.length > 0 ? (
            <SafetyParameterTable parameters={context.safetyParameters} />
          ) : (
            <Alert message="暂无安全关键参数" type="info" showIcon />
          )}
        </Card>
      ),
    },
  ]

  return (
    <div style={{ padding: 24, height: 'calc(100vh - 48px)' }}>
      <Space direction="vertical" size="middle" style={{ width: '100%', height: '100%' }}>
        {/* Header */}
        <div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => documentId && navigate(`/documents/${documentId}/design`)}
            style={{ marginBottom: 16 }}
          >
            返回设计文档
          </Button>
          <Title level={2} style={{ margin: 0 }}>
            设计文档审查
            {pendingCount > 0 && (
              <Badge
                count={pendingCount}
                style={{ marginLeft: 12, backgroundColor: '#ff4d4f' }}
              />
            )}
          </Title>
          <Text type="secondary">文档 ID: {documentId}</Text>
        </div>

        {error && <Alert message="错误" description={error} type="error" showIcon closable onClose={() => setError(null)} />}

        {/* Reviewer name input */}
        <div>
          <span style={{ marginRight: 8 }}>您的姓名:</span>
          <input
            type="text"
            value={reviewerName}
            onChange={(e) => handleReviewerNameChange(e.target.value)}
            placeholder="请输入您的姓名（用于修订和评审记录）"
            style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #d9d9d9', width: 320 }}
          />
        </div>

        {/* Status bar */}
        {designDoc?.status === 'completed' && (
          <Card size="small">
            <Space>
              <Tag color="green">设计文档已生成</Tag>
              {designDoc.asilLevel && <Tag>ASIL-{designDoc.asilLevel}</Tag>}
              {pendingCount > 0 ? (
                <Tag icon={<ExclamationCircleOutlined />} color="warning">
                  {pendingCount} 条未解决评审意见
                </Tag>
              ) : (
                <Tag icon={<CheckCircleOutlined />} color="success">
                  所有评审意见已解决
                </Tag>
              )}
              {pipelineStatus === 'design_reviewed' ? (
                <Tag color="blue">审查已提交</Tag>
              ) : (
                <Button
                  type="primary"
                  size="small"
                  onClick={handleSubmitReview}
                  loading={submitting}
                  disabled={pendingCount > 0}
                >
                  提交设计审查
                </Button>
              )}
            </Space>
          </Card>
        )}

        {designDoc?.status !== 'completed' && !loading && (
          <Alert
            message="设计文档尚未生成"
            description="请先返回设计文档页面，生成设计文档后再进入审查。"
            type="warning"
            showIcon
            action={
              <Button onClick={() => navigate(`/documents/${documentId}/design`)}>
                前往生成
              </Button>
            }
          />
        )}

        {/* Main split view */}
        {designDoc?.status === 'completed' && (
          <Splitter style={{ flex: 1, minHeight: 0 }}>
            <Splitter.Panel defaultSize="40%" min="25%" max="60%">
              <div style={{ paddingRight: 12, height: '100%', overflow: 'auto' }}>
                <Tabs defaultActiveKey="requirements" items={leftTabItems} />
              </div>
            </Splitter.Panel>
            <Splitter.Panel>
              <div style={{ paddingLeft: 12, height: '100%', overflow: 'auto' }}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {Object.entries(sections).map(([key, section]) => (
                    <SectionReviewCard
                      key={key}
                      sectionKey={key}
                      section={section}
                      documentId={documentId || ''}
                      comments={commentsMap[key] || []}
                      onSaveRevision={(content) => handleSaveRevision(key, content)}
                      onOpenHistory={() => openRevisionHistory(key)}
                      onAddComment={(text) => handleAddComment(key, text)}
                      onResolveComment={(id) => handleResolveComment(key, id)}
                      commentsLoading={commentsLoading[key] || false}
                    />
                  ))}
                </Space>
              </div>
            </Splitter.Panel>
          </Splitter>
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在加载审查上下文...</div>
          </div>
        )}
      </Space>

      <RevisionHistory
        visible={historyVisible}
        onClose={() => setHistoryVisible(false)}
        sectionKey={historySectionKey}
        sectionLabel={historySectionLabel}
        revisions={revisions}
        onRollback={handleRollback}
        loading={historyLoading}
      />
    </div>
  )
}

interface SectionReviewCardProps {
  sectionKey: string
  section: DesignSection
  documentId: string
  comments: ReviewComment[]
  onSaveRevision: (content: string) => void
  onOpenHistory: () => void
  onAddComment: (text: string) => void
  onResolveComment: (commentId: string) => void
  commentsLoading: boolean
}

const SectionReviewCard: React.FC<SectionReviewCardProps> = ({
  sectionKey,
  section,
  documentId,
  comments,
  onSaveRevision,
  onOpenHistory,
  onAddComment,
  onResolveComment,
  commentsLoading,
}) => {
  const config = sectionConfig[sectionKey] || { label: sectionKey, icon: null }
  const unresolvedCount = comments.filter((c) => !c.resolvedAt).length

  return (
    <Card
      title={
        <Space>
          {config.icon}
          <span>{config.label}</span>
          <Tag color="blue">Polarion: {section.polarionTraceId || '-'}</Tag>
          {unresolvedCount > 0 && (
            <Badge count={unresolvedCount} style={{ backgroundColor: '#ff4d4f' }} />
          )}
        </Space>
      }
      extra={
        <Button size="small" icon={<HistoryOutlined />} onClick={onOpenHistory}>
          修订历史
        </Button>
      }
    >
      <SectionEditor content={section.content || ''} onSave={onSaveRevision} storageKey={`modu_draft_${documentId}_${sectionKey}`} />
      <Divider style={{ margin: '16px 0' }} />
      <ReviewCommentPanel
        comments={comments}
        onAdd={onAddComment}
        onResolve={onResolveComment}
        loading={commentsLoading}
      />
    </Card>
  )
}

export default DesignReviewPage
