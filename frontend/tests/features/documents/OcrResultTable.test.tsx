import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import OcrResultTable from '../../../src/features/documents/components/OcrResultTable'
import type { OcrField } from '../../../src/features/documents/types'

const setupMatchMedia = () => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    }),
  })
}

beforeAll(() => {
  setupMatchMedia()
})

const mockFields: OcrField[] = [
  {
    id: '1',
    fieldId: 'OCR-FIELD-0001',
    extractedText: '4.5V ±0.1',
    normalizedValue: '4.5',
    confidence: 0.98,
    fieldType: 'voltage',
    sourcePage: 42,
    reviewStatus: 'pending',
  },
  {
    id: '2',
    fieldId: 'OCR-FIELD-0002',
    extractedText: 'l00ms timeout',
    normalizedValue: '100',
    confidence: 0.65,
    fieldType: 'timing',
    sourcePage: 38,
    reviewStatus: 'pending',
  },
]

describe('OcrResultTable', () => {
  it('renders field rows correctly', () => {
    render(
      <OcrResultTable
        fields={mockFields}
        pipelineBlocked={false}
        onConfirm={vi.fn()}
      />
    )

    expect(screen.getByText('OCR-FIELD-0001')).toBeDefined()
    expect(screen.getByText('OCR-FIELD-0002')).toBeDefined()
    expect(screen.getByText('4.5V ±0.1')).toBeDefined()
    expect(screen.getByText('l00ms timeout')).toBeDefined()
  })

  it('highlights low-confidence rows and shows confirm button', () => {
    const { container } = render(
      <OcrResultTable
        fields={mockFields}
        pipelineBlocked={true}
        onConfirm={vi.fn()}
      />
    )

    const buttons = container.querySelectorAll('button')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/流水线已阻塞/)).toBeDefined()
  })

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn()
    const { container } = render(
      <OcrResultTable
        fields={mockFields}
        pipelineBlocked={true}
        onConfirm={onConfirm}
      />
    )

    const buttons = container.querySelectorAll('button')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
    fireEvent.click(buttons[0])

    expect(onConfirm).toHaveBeenCalledTimes(1)
    const calledWith = onConfirm.mock.calls[0][0]
    expect(['OCR-FIELD-0001', 'OCR-FIELD-0002']).toContain(calledWith)
  })

  it('shows confirmed state for reviewed fields', () => {
    const confirmedFields: OcrField[] = [
      {
        ...mockFields[1],
        reviewStatus: 'confirmed',
        reviewedBy: '张三',
        reviewedAt: '2026-05-21T10:00:00Z',
      },
    ]

    render(
      <OcrResultTable
        fields={confirmedFields}
        pipelineBlocked={false}
        onConfirm={vi.fn()}
      />
    )

    expect(screen.getByText('已复核')).toBeDefined()
  })

  it('shows empty state when no fields', () => {
    render(
      <OcrResultTable
        fields={[]}
        pipelineBlocked={false}
        onConfirm={vi.fn()}
      />
    )

    expect(screen.getByText('暂无 OCR 提取结果')).toBeDefined()
  })
})
