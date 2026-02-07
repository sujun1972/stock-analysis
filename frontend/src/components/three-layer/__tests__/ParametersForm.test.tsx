/**
 * ParametersForm 组件单元测试
 *
 * 测试动态参数表单的渲染和交互
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ParametersForm } from '../ParametersForm'
import type { ParameterDef } from '@/lib/three-layer-types'

describe('ParametersForm', () => {
  const mockOnChange = jest.fn()

  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('空参数列表', () => {
    it('显示"无需配置参数"提示', () => {
      render(
        <ParametersForm
          parameters={[]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText(/无需配置参数/i)).toBeInTheDocument()
    })
  })

  describe('整数参数', () => {
    const integerParam: ParameterDef = {
      name: 'lookback_period',
      label: '回看周期',
      type: 'integer',
      default: 20,
      min_value: 1,
      max_value: 100,
      step: 1,
      description: '用于计算动量的历史周期',
    }

    it('渲染整数参数输入控件', () => {
      render(
        <ParametersForm
          parameters={[integerParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('回看周期')).toBeInTheDocument()
      expect(screen.getByText(/用于计算动量的历史周期/i)).toBeInTheDocument()
    })

    it('使用默认值', () => {
      render(
        <ParametersForm
          parameters={[integerParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      const input = screen.getByDisplayValue('20')
      expect(input).toBeInTheDocument()
    })

    it('可以修改参数值', () => {
      render(
        <ParametersForm
          parameters={[integerParam]}
          values={{ lookback_period: 20 }}
          onChange={mockOnChange}
        />
      )

      const input = screen.getByDisplayValue('20') as HTMLInputElement
      fireEvent.change(input, { target: { value: '30' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        lookback_period: 30,
      })
    })
  })

  describe('浮点数参数', () => {
    const floatParam: ParameterDef = {
      name: 'stop_loss_pct',
      label: '止损百分比',
      type: 'float',
      default: -5.0,
      min_value: -20.0,
      max_value: -1.0,
      step: 0.1,
      description: '触发止损的跌幅百分比',
    }

    it('渲染浮点数参数输入控件', () => {
      render(
        <ParametersForm
          parameters={[floatParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('止损百分比')).toBeInTheDocument()
    })

    it('处理浮点数值', () => {
      render(
        <ParametersForm
          parameters={[floatParam]}
          values={{ stop_loss_pct: -5.0 }}
          onChange={mockOnChange}
        />
      )

      const input = screen.getByDisplayValue('-5') as HTMLInputElement
      fireEvent.change(input, { target: { value: '-7.5' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        stop_loss_pct: -7.5,
      })
    })
  })

  describe('布尔参数', () => {
    const booleanParam: ParameterDef = {
      name: 'use_volume_filter',
      label: '使用成交量过滤',
      type: 'boolean',
      default: true,
      description: '是否过滤低成交量股票',
    }

    it('渲染布尔参数开关控件', () => {
      render(
        <ParametersForm
          parameters={[booleanParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('使用成交量过滤')).toBeInTheDocument()
    })

    it('切换布尔值', () => {
      render(
        <ParametersForm
          parameters={[booleanParam]}
          values={{ use_volume_filter: true }}
          onChange={mockOnChange}
        />
      )

      const switchElement = screen.getByRole('switch')
      fireEvent.click(switchElement)

      expect(mockOnChange).toHaveBeenCalledWith({
        use_volume_filter: false,
      })
    })
  })

  describe('选择参数', () => {
    const selectParam: ParameterDef = {
      name: 'signal_type',
      label: '信号类型',
      type: 'select',
      default: 'ma_cross',
      options: [
        { value: 'ma_cross', label: '均线交叉' },
        { value: 'rsi', label: 'RSI指标' },
        { value: 'macd', label: 'MACD指标' },
      ],
      description: '选择入场信号类型',
    }

    it('渲染选择参数下拉框', () => {
      render(
        <ParametersForm
          parameters={[selectParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('信号类型')).toBeInTheDocument()
    })

    it('选择选项', () => {
      render(
        <ParametersForm
          parameters={[selectParam]}
          values={{ signal_type: 'ma_cross' }}
          onChange={mockOnChange}
        />
      )

      const select = screen.getByDisplayValue('ma_cross') as HTMLSelectElement
      fireEvent.change(select, { target: { value: 'rsi' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        signal_type: 'rsi',
      })
    })
  })

  describe('字符串参数', () => {
    const stringParam: ParameterDef = {
      name: 'custom_formula',
      label: '自定义公式',
      type: 'string',
      default: 'close * volume',
      description: '输入自定义计算公式',
    }

    it('渲染字符串参数输入框', () => {
      render(
        <ParametersForm
          parameters={[stringParam]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('自定义公式')).toBeInTheDocument()
    })

    it('输入字符串', () => {
      render(
        <ParametersForm
          parameters={[stringParam]}
          values={{ custom_formula: 'close * volume' }}
          onChange={mockOnChange}
        />
      )

      const input = screen.getByDisplayValue('close * volume') as HTMLInputElement
      fireEvent.change(input, { target: { value: 'open + high' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        custom_formula: 'open + high',
      })
    })
  })

  describe('多参数组合', () => {
    const multipleParams: ParameterDef[] = [
      {
        name: 'lookback_period',
        label: '回看周期',
        type: 'integer',
        default: 20,
        min_value: 1,
        max_value: 100,
      },
      {
        name: 'top_n',
        label: '选股数量',
        type: 'integer',
        default: 50,
        min_value: 10,
        max_value: 200,
      },
      {
        name: 'use_volume_filter',
        label: '成交量过滤',
        type: 'boolean',
        default: true,
      },
    ]

    it('渲染多个参数', () => {
      render(
        <ParametersForm
          parameters={multipleParams}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText('回看周期')).toBeInTheDocument()
      expect(screen.getByText('选股数量')).toBeInTheDocument()
      expect(screen.getByText('成交量过滤')).toBeInTheDocument()
    })

    it('独立修改每个参数', () => {
      render(
        <ParametersForm
          parameters={multipleParams}
          values={{ lookback_period: 20, top_n: 50, use_volume_filter: true }}
          onChange={mockOnChange}
        />
      )

      // 修改第一个参数
      const lookbackInput = screen.getByDisplayValue('20') as HTMLInputElement
      fireEvent.change(lookbackInput, { target: { value: '30' } })

      expect(mockOnChange).toHaveBeenCalledWith({
        lookback_period: 30,
        top_n: 50,
        use_volume_filter: true,
      })
    })
  })

  describe('参数范围提示', () => {
    const paramWithRange: ParameterDef = {
      name: 'threshold',
      label: '阈值',
      type: 'float',
      default: 0.5,
      min_value: 0.0,
      max_value: 1.0,
      step: 0.01,
    }

    it('显示参数范围', () => {
      render(
        <ParametersForm
          parameters={[paramWithRange]}
          values={{}}
          onChange={mockOnChange}
        />
      )

      expect(screen.getByText(/范围.*0.*1/i)).toBeInTheDocument()
    })
  })
})
