import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RequirementTree from '../../../src/features/documents/components/RequirementTree'
import type { RequirementTreeNode } from '../../../src/features/documents/types'

describe('RequirementTree', () => {
  const mockRequirements: RequirementTreeNode[] = [
    {
      id: '1',
      requirementId: 'SW-REQ-001',
      description: 'System shall initialize registers',
      chapter: '3.1',
      asilLevel: 'B',
      children: [
        {
          id: '2',
          requirementId: 'SW-REQ-001-01',
          description: 'Initialize within 100ms',
          chapter: '3.1.1',
          asilLevel: 'B',
          children: [],
        },
      ],
    },
  ]

  it('renders requirement IDs and descriptions', () => {
    render(<RequirementTree requirements={mockRequirements} />)
    expect(screen.getByText('SW-REQ-001')).toBeDefined()
    expect(screen.getByText('System shall initialize registers')).toBeDefined()
    expect(screen.getByText('SW-REQ-001-01')).toBeDefined()
  })

  it('renders ASIL and chapter tags', () => {
    render(<RequirementTree requirements={mockRequirements} />)
    expect(screen.getAllByText('ASIL-B').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('章节 3.1')).toBeDefined()
  })

  it('renders empty array without error', () => {
    const { container } = render(<RequirementTree requirements={[]} />)
    expect(container.querySelector('.ant-tree')).toBeDefined()
  })
})
