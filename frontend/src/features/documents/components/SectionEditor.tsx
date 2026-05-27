import React, { useEffect, useState } from 'react'
import { Button, Input, Space } from 'antd'
import { EditOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons'

interface SectionEditorProps {
  content: string
  onSave: (newContent: string) => void
  disabled?: boolean
  storageKey?: string
}

const SectionEditor: React.FC<SectionEditorProps> = ({ content, onSave, disabled, storageKey }) => {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(() => {
    if (!storageKey) return content
    try {
      return localStorage.getItem(storageKey) || content
    } catch {
      return content
    }
  })

  useEffect(() => {
    if (!editing) {
      setDraft(content)
    }
  }, [content, editing])

  useEffect(() => {
    if (!storageKey) return
    try {
      localStorage.setItem(storageKey, draft)
    } catch {
      // ignore
    }
  }, [draft, storageKey])

  const handleSave = () => {
    onSave(draft)
    setEditing(false)
    if (storageKey) {
      try {
        localStorage.removeItem(storageKey)
      } catch {
        // ignore
      }
    }
  }

  const handleCancel = () => {
    setDraft(content)
    setEditing(false)
    if (storageKey) {
      try {
        localStorage.removeItem(storageKey)
      } catch {
        // ignore
      }
    }
  }

  if (editing) {
    return (
      <div>
        <Input.TextArea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={8}
          autoFocus
          disabled={disabled}
        />
        <Space style={{ marginTop: 8 }}>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={disabled}>
            保存修订
          </Button>
          <Button icon={<CloseOutlined />} onClick={handleCancel} disabled={disabled}>
            取消
          </Button>
        </Space>
      </div>
    )
  }

  return (
    <div>
      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>{content || '（无内容）'}</pre>
      <Button
        type="link"
        icon={<EditOutlined />}
        onClick={() => setEditing(true)}
        style={{ marginTop: 8 }}
      >
        编辑
      </Button>
    </div>
  )
}

export default SectionEditor
