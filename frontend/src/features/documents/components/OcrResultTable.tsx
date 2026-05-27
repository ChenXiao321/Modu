import React from 'react'
import { Table, Tag, Button, Space, Tooltip } from 'antd'
import { CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import type { OcrField } from '../types'

interface OcrResultTableProps {
  fields: OcrField[]
  pipelineBlocked: boolean
  onConfirm: (fieldId: string) => void
  confirmingFieldId?: string | null
}

const OcrResultTable: React.FC<OcrResultTableProps> = ({
  fields,
  pipelineBlocked,
  onConfirm,
  confirmingFieldId,
}) => {
  const columns = [
    {
      title: '字段编号',
      dataIndex: 'fieldId',
      key: 'fieldId',
      width: 140,
    },
    {
      title: '提取文本',
      dataIndex: 'extractedText',
      key: 'extractedText',
      render: (text: string) => <span style={{ fontFamily: 'monospace' }}>{text}</span>,
    },
    {
      title: '归一化值',
      dataIndex: 'normalizedValue',
      key: 'normalizedValue',
      width: 120,
      render: (value?: string) => value || '-',
    },
    {
      title: '类型',
      dataIndex: 'fieldType',
      key: 'fieldType',
      width: 100,
      render: (type?: string) => type ? <Tag>{type}</Tag> : '-',
    },
    {
      title: '页码',
      dataIndex: 'sourcePage',
      key: 'sourcePage',
      width: 80,
      render: (page?: number) => page ?? '-',
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      sorter: (a: OcrField, b: OcrField) => {
        const av = Number.isFinite(a.confidence) ? a.confidence : 0
        const bv = Number.isFinite(b.confidence) ? b.confidence : 0
        return av - bv
      },
      render: (confidence: number) => {
        let color = 'green'
        if (confidence < 0.95) color = 'red'
        else if (confidence < 0.98) color = 'orange'
        return (
          <Tag color={color}>
            {(confidence * 100).toFixed(1)}%
          </Tag>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'reviewStatus',
      key: 'reviewStatus',
      width: 120,
      render: (status: string, record: OcrField) => {
        if (status === 'confirmed') {
          return (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已复核
            </Tag>
          )
        }
        if (record.confidence < 0.95) {
          return (
            <Tag icon={<ExclamationCircleOutlined />} color="error">
              需复核
            </Tag>
          )
        }
        return <Tag color="default">待复核</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: OcrField) => {
        if (record.reviewStatus === 'confirmed') {
          return <span style={{ color: '#999' }}>已确认</span>
        }
        if (record.confidence < 0.95) {
          return (
            <Tooltip title="确认该字段提取正确，解除流水线阻塞">
              <Button
                type="primary"
                danger
                size="small"
                loading={confirmingFieldId === record.fieldId}
                onClick={() => onConfirm(record.fieldId)}
              >
                确认
              </Button>
            </Tooltip>
          )
        }
        return (
          <Button
            size="small"
            loading={confirmingFieldId === record.fieldId}
            onClick={() => onConfirm(record.fieldId)}
          >
            确认
          </Button>
        )
      },
    },
  ]

  const rowClassName = (record: OcrField) => {
    if (record.confidence < 0.95 && record.reviewStatus !== 'confirmed') {
      return 'ocr-low-confidence-row'
    }
    return ''
  }

  const rowStyle = { backgroundColor: '#fff2f0' }

  return (
    <div>
      {pipelineBlocked && (
        <div style={{ marginBottom: 16, padding: 12, background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 4 }}>
          <Space>
            <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
            <span style={{ color: '#cf1322', fontWeight: 500 }}>
              流水线已阻塞：存在未复核的低置信度 OCR 字段，请确认后方可进入方案设计阶段。
            </span>
          </Space>
        </div>
      )}
      <Table
        columns={columns}
        dataSource={fields}
        rowKey="fieldId"
        rowClassName={rowClassName}
        onRow={(record) => ({
          style: record.confidence < 0.95 && record.reviewStatus !== 'confirmed' ? rowStyle : {},
        })}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无 OCR 提取结果' }}
      />
    </div>
  )
}

export default OcrResultTable
