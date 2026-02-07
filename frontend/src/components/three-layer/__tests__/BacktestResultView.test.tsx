/**
 * BacktestResultView 组件单元测试
 *
 * 测试回测结果展示组件的核心功能
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { BacktestResultView } from '../BacktestResultView'
import type { BacktestResult } from '@/lib/three-layer-types'

// Mock ECharts 和 toast
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}))

jest.mock('echarts', () => ({
  init: jest.fn(() => ({
    setOption: jest.fn(),
    resize: jest.fn(),
    dispose: jest.fn(),
  })),
}))

describe('BacktestResultView', () => {
  const mockResult: BacktestResult = {
    status: 'success',
    data: {
      total_return: 0.25,
      annualized_return: 0.15,
      sharpe_ratio: 1.5,
      max_drawdown: -0.10,
      win_rate: 0.65,
      total_trades: 20,
      sortino_ratio: 1.8,
      calmar_ratio: 1.2,
      volatility: 0.12,
      daily_portfolio: [
        { date: '2024-01-01', value: 100000 },
        { date: '2024-01-02', value: 102000 },
        { date: '2024-01-03', value: 105000 },
      ],
      trades: [
        {
          date: '2024-01-01',
          action: 'buy',
          stock_code: '600000.SH',
          price: 10.0,
          shares: 100,
        },
        {
          date: '2024-01-05',
          action: 'sell',
          stock_code: '600000.SH',
          price: 12.0,
          shares: 100,
        },
      ],
    },
  }

  it('渲染回测结果标题', () => {
    render(<BacktestResultView result={mockResult} />)

    expect(screen.getByText('回测结果')).toBeInTheDocument()
  })

  it('显示绩效指标', () => {
    render(<BacktestResultView result={mockResult} />)

    expect(screen.getByText('绩效指标')).toBeInTheDocument()
  })

  it('显示操作按钮', () => {
    render(<BacktestResultView result={mockResult} />)

    expect(screen.getByRole('button', { name: /保存到历史/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /分享结果/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /导出报告/i })).toBeInTheDocument()
  })

  it('显示交易统计', () => {
    render(<BacktestResultView result={mockResult} />)

    expect(screen.getByText('交易统计')).toBeInTheDocument()
    expect(screen.getByText(/总交易次数.*20次/i)).toBeInTheDocument()
  })

  it('显示Tab切换（净值曲线和回撤曲线）', () => {
    render(<BacktestResultView result={mockResult} />)

    expect(screen.getByRole('tab', { name: /净值曲线/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /回撤曲线/i })).toBeInTheDocument()
  })

  it('没有数据时不渲染', () => {
    const emptyResult: BacktestResult = {
      status: 'success',
      data: null as any,
    }

    const { container } = render(<BacktestResultView result={emptyResult} />)
    expect(container.firstChild).toBeNull()
  })
})
