import { describe, it, expect, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import SafetyParameterTable from '../../../src/features/documents/components/SafetyParameterTable'
import type { SafetyParameter } from '../../../src/features/documents/types'

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

describe('SafetyParameterTable', () => {
  beforeAll(() => {
    setupMatchMedia()
  })

  it('renders empty state when no parameters', () => {
    render(<SafetyParameterTable parameters={[]} />)
    expect(screen.getByText('未检测到安全关键参数')).toBeDefined()
    expect(
      screen.getByText(/该文档尚未解析完成或未识别到安全相关参数/)
    ).toBeDefined()
  })

  it('renders parameter rows correctly', () => {
    const parameters: SafetyParameter[] = [
      {
        id: 'uuid-1',
        parameterId: 'SW-REQ-SAF-001',
        name: '供电电压阈值',
        value: '4.5',
        unit: 'V',
        tolerance: '±0.1',
        chapter: '3.2.1',
        sourcePage: 42,
      },
      {
        id: 'uuid-2',
        parameterId: 'SW-REQ-SAF-002',
        name: '工作温度范围',
        value: '-40 ~ 150',
        unit: '°C',
        tolerance: undefined,
        chapter: '3.2.2',
        sourcePage: undefined,
      },
    ]

    render(<SafetyParameterTable parameters={parameters} />)

    expect(screen.getByText('SW-REQ-SAF-001')).toBeDefined()
    expect(screen.getByText('供电电压阈值')).toBeDefined()
    expect(screen.getByText('4.5')).toBeDefined()
    expect(screen.getByText('V')).toBeDefined()
    expect(screen.getByText('±0.1')).toBeDefined()
    expect(screen.getByText(/章节 3.2.1/)).toBeDefined()
    expect(screen.getByText(/第 42 页/)).toBeDefined()

    expect(screen.getByText('SW-REQ-SAF-002')).toBeDefined()
    expect(screen.getByText('工作温度范围')).toBeDefined()
    expect(screen.getByText('-40 ~ 150')).toBeDefined()
    expect(screen.getByText('°C')).toBeDefined()
  })

  it('shows dash for missing tolerance and page', () => {
    const parameters: SafetyParameter[] = [
      {
        id: 'uuid-1',
        parameterId: 'SW-REQ-SAF-003',
        name: '看门狗周期',
        value: '50',
        unit: 'ms',
      },
    ]

    render(<SafetyParameterTable parameters={parameters} />)
    expect(screen.getByText('SW-REQ-SAF-003')).toBeDefined()
    // Table renders "—" for missing optional fields
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
  })
})
