/**
 * 三层架构API单元测试
 * 使用 Jest 和 axios-mock-adapter
 */

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'
import {
  threeLayerApi,
  ThreeLayerApiError,
} from '../three-layer-api'
import type {
  SelectorInfo,
  EntryInfo,
  ExitInfo,
  StrategyConfig,
  ValidationResult,
  BacktestResult,
} from '../three-layer-types'

// 创建 axios mock
const mock = new MockAdapter(axios)

// 测试数据
const mockSelectors: SelectorInfo[] = [
  {
    id: 'momentum',
    name: '动量选股',
    description: '基于股票价格动量选择强势股票',
    version: '1.0.0',
    parameters: [
      {
        name: 'lookback_period',
        label: '回看周期',
        type: 'integer',
        default: 20,
        min_value: 5,
        max_value: 60,
        description: '计算动量的天数',
      },
      {
        name: 'top_n',
        label: '选股数量',
        type: 'integer',
        default: 50,
        min_value: 10,
        max_value: 100,
      },
    ],
  },
]

const mockEntries: EntryInfo[] = [
  {
    id: 'immediate',
    name: '立即入场',
    description: '候选池股票立即买入',
    version: '1.0.0',
    parameters: [],
  },
]

const mockExits: ExitInfo[] = [
  {
    id: 'fixed_stop_loss',
    name: '固定止损',
    description: '固定百分比止损',
    version: '1.0.0',
    parameters: [
      {
        name: 'stop_loss_pct',
        label: '止损百分比',
        type: 'float',
        default: -5.0,
        min_value: -20.0,
        max_value: 0.0,
        step: 0.1,
        description: '亏损达到该百分比时卖出',
      },
    ],
  },
]

const mockValidationSuccess: ValidationResult = {
  valid: true,
  errors: [],
  warnings: [],
}

const mockBacktestResult: BacktestResult = {
  status: 'success',
  data: {
    total_return: 0.25,
    annualized_return: 0.18,
    sharpe_ratio: 1.5,
    max_drawdown: -0.12,
    win_rate: 0.6,
    total_trades: 50,
    daily_portfolio: [
      { date: '2024-01-01', value: 100000 },
      { date: '2024-01-02', value: 101000 },
    ],
    trades: [
      {
        date: '2024-01-01',
        action: 'buy',
        stock_code: '600000.SH',
        price: 10.0,
        shares: 1000,
      },
    ],
  },
}

describe('ThreeLayerAPI', () => {
  beforeEach(() => {
    // 重置所有 mock
    mock.reset()
  })

  afterAll(() => {
    // 恢复 axios
    mock.restore()
  })

  describe('getSelectors', () => {
    it('should fetch selectors successfully', async () => {
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: mockSelectors,
      })

      const selectors = await threeLayerApi.getSelectors()

      expect(selectors).toEqual(mockSelectors)
      expect(selectors).toHaveLength(1)
      expect(selectors[0].id).toBe('momentum')
    })

    it('should return empty array when no data', async () => {
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: null,
      })

      const selectors = await threeLayerApi.getSelectors()

      expect(selectors).toEqual([])
    })

    it('should handle network error', async () => {
      mock.onGet('/api/three-layer/selectors').networkError()

      await expect(threeLayerApi.getSelectors()).rejects.toThrow(
        ThreeLayerApiError
      )
    })

    it('should retry on 500 error', async () => {
      mock
        .onGet('/api/three-layer/selectors')
        .replyOnce(500)
        .onGet('/api/three-layer/selectors')
        .reply(200, { status: 'success', data: mockSelectors })

      const selectors = await threeLayerApi.getSelectors()

      expect(selectors).toEqual(mockSelectors)
    })
  })

  describe('getEntries', () => {
    it('should fetch entries successfully', async () => {
      mock.onGet('/api/three-layer/entries').reply(200, {
        status: 'success',
        data: mockEntries,
      })

      const entries = await threeLayerApi.getEntries()

      expect(entries).toEqual(mockEntries)
      expect(entries).toHaveLength(1)
      expect(entries[0].id).toBe('immediate')
    })
  })

  describe('getExits', () => {
    it('should fetch exits successfully', async () => {
      mock.onGet('/api/three-layer/exits').reply(200, {
        status: 'success',
        data: mockExits,
      })

      const exits = await threeLayerApi.getExits()

      expect(exits).toEqual(mockExits)
      expect(exits).toHaveLength(1)
      expect(exits[0].id).toBe('fixed_stop_loss')
    })
  })

  describe('getAllComponents', () => {
    it('should fetch all components in parallel', async () => {
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: mockSelectors,
      })
      mock.onGet('/api/three-layer/entries').reply(200, {
        status: 'success',
        data: mockEntries,
      })
      mock.onGet('/api/three-layer/exits').reply(200, {
        status: 'success',
        data: mockExits,
      })

      const result = await threeLayerApi.getAllComponents()

      expect(result.selectors).toEqual(mockSelectors)
      expect(result.entries).toEqual(mockEntries)
      expect(result.exits).toEqual(mockExits)
    })
  })

  describe('validateStrategy', () => {
    const mockConfig: StrategyConfig = {
      selector_id: 'momentum',
      selector_params: { lookback_period: 20, top_n: 50 },
      entry_id: 'immediate',
      entry_params: {},
      exit_id: 'fixed_stop_loss',
      exit_params: { stop_loss_pct: -5.0 },
      stock_codes: ['600000.SH'],
      start_date: '2024-01-01',
      end_date: '2024-12-31',
    }

    it('should validate strategy successfully', async () => {
      mock.onPost('/api/three-layer/validate').reply(200, {
        status: 'success',
        data: mockValidationSuccess,
      })

      const result = await threeLayerApi.validateStrategy(mockConfig)

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should return validation errors', async () => {
      const mockValidationError: ValidationResult = {
        valid: false,
        errors: ['开始日期必须早于结束日期'],
        warnings: [],
      }

      mock.onPost('/api/three-layer/validate').reply(200, {
        status: 'success',
        data: mockValidationError,
      })

      const result = await threeLayerApi.validateStrategy(mockConfig)

      expect(result.valid).toBe(false)
      expect(result.errors).toHaveLength(1)
    })
  })

  describe('runBacktest', () => {
    const mockConfig: StrategyConfig = {
      selector_id: 'momentum',
      selector_params: { lookback_period: 20, top_n: 50 },
      entry_id: 'immediate',
      entry_params: {},
      exit_id: 'fixed_stop_loss',
      exit_params: { stop_loss_pct: -5.0 },
      stock_codes: ['600000.SH'],
      start_date: '2024-01-01',
      end_date: '2024-12-31',
    }

    it('should run backtest successfully', async () => {
      mock.onPost('/api/three-layer/backtest').reply(200, {
        status: 'success',
        data: mockBacktestResult,
      })

      const result = await threeLayerApi.runBacktest(mockConfig)

      expect(result.status).toBe('success')
      expect(result.data).toBeDefined()
      expect(result.data?.total_return).toBe(0.25)
    })

    it('should handle backtest error', async () => {
      mock.onPost('/api/three-layer/backtest').reply(500, {
        message: '回测执行失败',
      })

      const result = await threeLayerApi.runBacktest(mockConfig)

      expect(result.status).toBe('error')
      expect(result.error).toBeDefined()
    })

    it('should handle timeout error', async () => {
      mock.onPost('/api/three-layer/backtest').timeout()

      const result = await threeLayerApi.runBacktest(mockConfig)

      expect(result.status).toBe('error')
    })
  })

  describe('getSelectorById', () => {
    it('should get selector by id', async () => {
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: mockSelectors,
      })

      const selector = await threeLayerApi.getSelectorById('momentum')

      expect(selector).toBeDefined()
      expect(selector?.id).toBe('momentum')
      expect(selector?.parameters).toHaveLength(2)
    })

    it('should return null for non-existent id', async () => {
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: mockSelectors,
      })

      const selector = await threeLayerApi.getSelectorById('non-existent')

      expect(selector).toBeNull()
    })
  })

  describe('getEntryById', () => {
    it('should get entry by id', async () => {
      mock.onGet('/api/three-layer/entries').reply(200, {
        status: 'success',
        data: mockEntries,
      })

      const entry = await threeLayerApi.getEntryById('immediate')

      expect(entry).toBeDefined()
      expect(entry?.id).toBe('immediate')
    })
  })

  describe('getExitById', () => {
    it('should get exit by id', async () => {
      mock.onGet('/api/three-layer/exits').reply(200, {
        status: 'success',
        data: mockExits,
      })

      const exit = await threeLayerApi.getExitById('fixed_stop_loss')

      expect(exit).toBeDefined()
      expect(exit?.id).toBe('fixed_stop_loss')
    })
  })

  describe('validateParameter', () => {
    it('should validate integer parameter', () => {
      const param = {
        name: 'lookback_period',
        type: 'integer',
        min_value: 5,
        max_value: 60,
      }

      const result1 = threeLayerApi.validateParameter(param, 20)
      expect(result1.valid).toBe(true)

      const result2 = threeLayerApi.validateParameter(param, 3)
      expect(result2.valid).toBe(false)
      expect(result2.error).toContain('不能小于')

      const result3 = threeLayerApi.validateParameter(param, 70)
      expect(result3.valid).toBe(false)
      expect(result3.error).toContain('不能大于')

      const result4 = threeLayerApi.validateParameter(param, 20.5)
      expect(result4.valid).toBe(false)
      expect(result4.error).toContain('必须是整数')
    })

    it('should validate float parameter', () => {
      const param = {
        name: 'stop_loss_pct',
        type: 'float',
        min_value: -20.0,
        max_value: 0.0,
      }

      const result1 = threeLayerApi.validateParameter(param, -5.0)
      expect(result1.valid).toBe(true)

      const result2 = threeLayerApi.validateParameter(param, -25.0)
      expect(result2.valid).toBe(false)
    })

    it('should validate boolean parameter', () => {
      const param = { name: 'enabled', type: 'boolean' }

      const result1 = threeLayerApi.validateParameter(param, true)
      expect(result1.valid).toBe(true)

      const result2 = threeLayerApi.validateParameter(param, 'true')
      expect(result2.valid).toBe(false)
      expect(result2.error).toContain('必须是布尔值')
    })
  })

  describe('clientValidateStrategy', () => {
    beforeEach(() => {
      // Mock 组件获取
      mock.onGet('/api/three-layer/selectors').reply(200, {
        status: 'success',
        data: mockSelectors,
      })
      mock.onGet('/api/three-layer/entries').reply(200, {
        status: 'success',
        data: mockEntries,
      })
      mock.onGet('/api/three-layer/exits').reply(200, {
        status: 'success',
        data: mockExits,
      })
    })

    it('should validate complete strategy config', async () => {
      const config: StrategyConfig = {
        selector_id: 'momentum',
        selector_params: { lookback_period: 20, top_n: 50 },
        entry_id: 'immediate',
        entry_params: {},
        exit_id: 'fixed_stop_loss',
        exit_params: { stop_loss_pct: -5.0 },
        stock_codes: ['600000.SH'],
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      }

      const result = await threeLayerApi.clientValidateStrategy(config)

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should detect missing required fields', async () => {
      const config: StrategyConfig = {
        selector_id: '',
        selector_params: {},
        entry_id: '',
        entry_params: {},
        exit_id: '',
        exit_params: {},
        stock_codes: [],
        start_date: '',
        end_date: '',
      }

      const result = await threeLayerApi.clientValidateStrategy(config)

      expect(result.valid).toBe(false)
      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors).toContain('请选择选股器')
      expect(result.errors).toContain('请选择入场策略')
      expect(result.errors).toContain('请选择退出策略')
    })

    it('should detect invalid date range', async () => {
      const config: StrategyConfig = {
        selector_id: 'momentum',
        selector_params: { lookback_period: 20, top_n: 50 },
        entry_id: 'immediate',
        entry_params: {},
        exit_id: 'fixed_stop_loss',
        exit_params: { stop_loss_pct: -5.0 },
        stock_codes: ['600000.SH'],
        start_date: '2024-12-31',
        end_date: '2024-01-01',
      }

      const result = await threeLayerApi.clientValidateStrategy(config)

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('开始日期必须早于结束日期')
    })

    it('should detect invalid parameter values', async () => {
      const config: StrategyConfig = {
        selector_id: 'momentum',
        selector_params: { lookback_period: 100, top_n: 50 }, // 超出范围
        entry_id: 'immediate',
        entry_params: {},
        exit_id: 'fixed_stop_loss',
        exit_params: { stop_loss_pct: -5.0 },
        stock_codes: ['600000.SH'],
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      }

      const result = await threeLayerApi.clientValidateStrategy(config)

      expect(result.valid).toBe(false)
      expect(result.errors.some((e) => e.includes('不能大于'))).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('should throw ThreeLayerApiError on 404', async () => {
      mock.onGet('/api/three-layer/selectors').reply(404, {
        message: 'Not Found',
      })

      await expect(threeLayerApi.getSelectors()).rejects.toThrow(
        ThreeLayerApiError
      )
    })

    it('should throw ThreeLayerApiError on 401', async () => {
      mock.onGet('/api/three-layer/selectors').reply(401, {
        message: 'Unauthorized',
      })

      await expect(threeLayerApi.getSelectors()).rejects.toThrow(
        ThreeLayerApiError
      )
    })

    it('should handle network timeout', async () => {
      mock.onGet('/api/three-layer/selectors').timeout()

      await expect(threeLayerApi.getSelectors()).rejects.toThrow()
    })
  })

  describe('Retry Logic', () => {
    it('should retry on 503 error and succeed', async () => {
      mock
        .onGet('/api/three-layer/selectors')
        .replyOnce(503)
        .onGet('/api/three-layer/selectors')
        .reply(200, { status: 'success', data: mockSelectors })

      const selectors = await threeLayerApi.getSelectors()

      expect(selectors).toEqual(mockSelectors)
    })

    it('should retry multiple times before failing', async () => {
      mock
        .onGet('/api/three-layer/selectors')
        .replyOnce(503)
        .onGet('/api/three-layer/selectors')
        .replyOnce(503)
        .onGet('/api/three-layer/selectors')
        .replyOnce(503)
        .onGet('/api/three-layer/selectors')
        .reply(503)

      await expect(threeLayerApi.getSelectors()).rejects.toThrow()
    })

    it('should not retry on 400 error', async () => {
      mock.onGet('/api/three-layer/selectors').reply(400, {
        message: 'Bad Request',
      })

      await expect(threeLayerApi.getSelectors()).rejects.toThrow(
        ThreeLayerApiError
      )

      // 验证只调用了一次（没有重试）
      expect(mock.history.get.length).toBe(1)
    })
  })
})
