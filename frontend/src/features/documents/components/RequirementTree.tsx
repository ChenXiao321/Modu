import React from 'react'
import { Tree, Tag, Typography, Space } from 'antd'
import type { DataNode } from 'antd/es/tree'
import type { RequirementTreeNode } from '../types'

interface RequirementTreeProps {
  requirements: RequirementTreeNode[]
}

const { Text } = Typography

const MAX_TREE_DEPTH = 10

function buildTreeData(nodes: RequirementTreeNode[], depth = 1): DataNode[] {
  if (depth > MAX_TREE_DEPTH) {
    return []
  }
  return nodes.map((node) => ({
    key: node.id,
    title: (
      <Space direction="vertical" size={0} style={{ padding: '4px 0' }}>
        <Space>
          <Text strong>{node.requirementId}</Text>
          {node.asilLevel && (
            <Tag color="red">ASIL-{node.asilLevel}</Tag>
          )}
          {node.chapter && (
            <Tag color="blue">章节 {node.chapter}</Tag>
          )}
        </Space>
        <Text type="secondary" style={{ whiteSpace: 'normal' }}>
          {node.description}
        </Text>
      </Space>
    ),
    children: buildTreeData(node.children, depth + 1),
  }))
}

const RequirementTree: React.FC<RequirementTreeProps> = ({ requirements }) => {
  const treeData = buildTreeData(requirements)

  return (
    <Tree
      treeData={treeData}
      defaultExpandAll
      showLine
      style={{ background: '#fafafa', padding: 16, borderRadius: 8 }}
    />
  )
}

export default RequirementTree
