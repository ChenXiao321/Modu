import React from 'react'
import { Table, Tag, Empty, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { SafetyParameter } from '../types'

interface SafetyParameterTableProps {
  parameters: SafetyParameter[]
}

const { Text } = Typography

const columns: ColumnsType<SafetyParameter> = [
  {
    title: '参数编号',
    dataIndex: 'parameterId',
    key: 'parameterId',
    render: (text: string) => (<Text strong>{text}</Text>),
    width: 160,
  },
  {
    title: '参数名',
    dataIndex: 'name',
    key: 'name',
    width: 200,
  },
  {
    title: '数值',
    dataIndex: 'value',
    key: 'value',
    render: (value: string, record: SafetyParameter) => (
      <span>
        {value}
        {record.unit && <Tag style={{ marginLeft: 4 }}>{record.unit}</Tag>}
      </span>
    ),
    width: 140,
  },
  {
    title: '容差',
    dataIndex: 'tolerance',
    key: 'tolerance',
    render: (tolerance: string | undefined) =>
      tolerance ? tolerance : '—',
    width: 120,
  },
  {
    title: '来源章节',
    dataIndex: 'chapter',
    key: 'chapter',
    render: (chapter: string | undefined) =>
      chapter ? <Tag color="blue">章节 {chapter}</Tag> : '—',
    width: 140,
  },
  {
    title: '来源页码',
    dataIndex: 'sourcePage',
    key: 'sourcePage',
    render: (page: number | undefined) =>
      page ? <Text type="secondary">第 {page} 页</Text> : '—',
    width: 120,
  },
]

const SafetyParameterTable: React.FC<SafetyParameterTableProps> = ({ parameters }) => {
  if (parameters.length === 0) {
    return (
      <Empty
        description={
          <span>
            未检测到安全关键参数
            <br />
            <Text type="secondary">该文档尚未解析完成或未识别到安全相关参数</Text>
          </span>
        }
      />
    )
  }

  return (
    <Table
      dataSource={parameters}
      columns={columns}
      rowKey="id"
      pagination={false}
      size="middle"
      bordered
    />
  )
}

export default SafetyParameterTable
