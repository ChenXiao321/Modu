import React, { useState } from 'react'
import { Button, Input, List, Tag, Space, Typography, Empty } from 'antd'
import { CommentOutlined, CheckCircleOutlined } from '@ant-design/icons'
import type { ReviewComment } from '../types'

const { Text } = Typography

interface ReviewCommentPanelProps {
  comments: ReviewComment[]
  onAdd: (text: string) => void
  onResolve: (commentId: string) => void
  loading?: boolean
}

const ReviewCommentPanel: React.FC<ReviewCommentPanelProps> = ({
  comments,
  onAdd,
  onResolve,
  loading,
}) => {
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [resolvingId, setResolvingId] = useState<string | null>(null)

  const handleAdd = async () => {
    if (!draft.trim()) return
    setSending(true)
    try {
      await onAdd(draft.trim())
      setDraft('')
    } finally {
      setSending(false)
    }
  }

  const handleResolve = async (commentId: string) => {
    setResolvingId(commentId)
    try {
      await onResolve(commentId)
    } finally {
      setResolvingId(null)
    }
  }

  const unresolved = comments.filter((c) => !c.resolvedAt)
  const resolved = comments.filter((c) => c.resolvedAt)

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          placeholder="输入评审意见..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onPressEnter={handleAdd}
        />
        <Button type="primary" icon={<CommentOutlined />} onClick={handleAdd} loading={sending} disabled={loading}>
          添加
        </Button>
      </Space.Compact>

      {unresolved.length === 0 && resolved.length === 0 && <Empty description="暂无评审意见" />}

      {unresolved.length > 0 && (
        <List
          size="small"
          header={<Text type="danger">未解决 ({unresolved.length})</Text>}
          dataSource={unresolved}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  size="small"
                  type="link"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleResolve(item.id)}
                  loading={resolvingId === item.id}
                  disabled={sending || resolvingId !== null}
                >
                  解决
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.author}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.createdAt).toLocaleString()}
                    </Text>
                    <Tag color="red">未解决</Tag>
                  </Space>
                }
                description={item.commentText}
              />
            </List.Item>
          )}
        />
      )}

      {resolved.length > 0 && (
        <List
          size="small"
          header={<Text type="secondary">已解决 ({resolved.length})</Text>}
          dataSource={resolved}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>{item.author}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.createdAt).toLocaleString()}
                    </Text>
                    <Tag color="green">已解决</Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical">
                    <Text>{item.commentText}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      由 {item.resolvedBy} 于 {item.resolvedAt ? new Date(item.resolvedAt).toLocaleString() : '-'} 解决
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Space>
  )
}

export default ReviewCommentPanel
