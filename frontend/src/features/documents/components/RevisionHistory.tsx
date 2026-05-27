import React from 'react'
import { Drawer, Button, Timeline, Typography, Space, Empty } from 'antd'
import { RollbackOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { DesignRevisionWithDiff } from '../types'

const { Text, Paragraph } = Typography

interface RevisionHistoryProps {
  visible: boolean
  onClose: () => void
  sectionKey: string
  sectionLabel: string
  revisions: DesignRevisionWithDiff[]
  onRollback: (revisionId: string) => void
  loading?: boolean
}

const RevisionHistory: React.FC<RevisionHistoryProps> = ({
  visible,
  onClose,
  sectionLabel,
  revisions,
  onRollback,
  loading,
}) => {
  return (
    <Drawer
      title={`修订历史 — ${sectionLabel}`}
      placement="right"
      width={720}
      onClose={onClose}
      open={visible}
    >
      {revisions.length === 0 ? (
        <Empty description="暂无修订记录" />
      ) : (
        <Timeline mode="left">
          {revisions.map((r) => (
            <Timeline.Item key={r.id} dot={<ClockCircleOutlined />}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Text strong>{r.author}</Text>
                  <Text type="secondary">{new Date(r.createdAt).toLocaleString()}</Text>
                </Space>
                <Paragraph style={{ margin: 0 }}>
                  <pre
                    style={{
                      background: '#f6f8fa',
                      padding: 12,
                      borderRadius: 6,
                      overflow: 'auto',
                      maxHeight: 300,
                      fontSize: 12,
                    }}
                  >
                    {(r.diff || '（无差异）').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}
                  </pre>
                </Paragraph>
                <Button
                  size="small"
                  icon={<RollbackOutlined />}
                  onClick={() => onRollback(r.id)}
                  loading={loading}
                >
                  回退到此版本
                </Button>
              </Space>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Drawer>
  )
}

export default RevisionHistory
