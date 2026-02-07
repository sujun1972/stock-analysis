/**
 * position-analysis 工具函数单元测试
 *
 * 测试持仓分析算法的正确性
 */

import {
  analyzePositions,
  calculatePositionStats,
  calculateDrawdown,
} from '../position-analysis'
import type { Trade, DailyPortfolio } from '@/lib/three-layer-types'

describe('position-analysis', () => {
  describe('analyzePositions', () => {
    it('正确配对买入和卖出交易（FIFO）', () => {
      const trades: Trade[] = [
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
      ]

      const positions = analyzePositions(trades)

      expect(positions).toHaveLength(1)
      expect(positions[0]).toMatchObject({
        stockCode: '600000.SH',
        buyDate: '2024-01-01',
        sellDate: '2024-01-05',
        buyPrice: 10.0,
        sellPrice: 12.0,
        shares: 100,
        holdingDays: 4,
        returnRate: 0.2, // (12-10)/10 = 20%
        profit: 200, // (12-10)*100
      })
    })

    it('处理多笔交易（FIFO顺序）', () => {
      const trades: Trade[] = [
        { date: '2024-01-01', action: 'buy', stock_code: '600000.SH', price: 10.0, shares: 100 },
        { date: '2024-01-02', action: 'buy', stock_code: '600000.SH', price: 11.0, shares: 100 },
        { date: '2024-01-05', action: 'sell', stock_code: '600000.SH', price: 12.0, shares: 100 },
        { date: '2024-01-06', action: 'sell', stock_code: '600000.SH', price: 13.0, shares: 100 },
      ]

      const positions = analyzePositions(trades)

      expect(positions).toHaveLength(2)

      // 第一笔：1月1日买入 → 1月5日卖出
      expect(positions[0].buyDate).toBe('2024-01-01')
      expect(positions[0].sellDate).toBe('2024-01-05')
      expect(positions[0].profit).toBe(200) // (12-10)*100

      // 第二笔：1月2日买入 → 1月6日卖出
      expect(positions[1].buyDate).toBe('2024-01-02')
      expect(positions[1].sellDate).toBe('2024-01-06')
      expect(positions[1].profit).toBe(200) // (13-11)*100
    })

    it('处理亏损交易', () => {
      const trades: Trade[] = [
        { date: '2024-01-01', action: 'buy', stock_code: '600000.SH', price: 10.0, shares: 100 },
        { date: '2024-01-05', action: 'sell', stock_code: '600000.SH', price: 8.0, shares: 100 },
      ]

      const positions = analyzePositions(trades)

      expect(positions[0].returnRate).toBe(-0.2) // -20%
      expect(positions[0].profit).toBe(-200)
    })

    it('处理不同股票的交易', () => {
      const trades: Trade[] = [
        { date: '2024-01-01', action: 'buy', stock_code: '600000.SH', price: 10.0, shares: 100 },
        { date: '2024-01-01', action: 'buy', stock_code: '000001.SZ', price: 20.0, shares: 50 },
        { date: '2024-01-05', action: 'sell', stock_code: '600000.SH', price: 12.0, shares: 100 },
        { date: '2024-01-06', action: 'sell', stock_code: '000001.SZ', price: 22.0, shares: 50 },
      ]

      const positions = analyzePositions(trades)

      expect(positions).toHaveLength(2)
      expect(positions.some(p => p.stockCode === '600000.SH')).toBe(true)
      expect(positions.some(p => p.stockCode === '000001.SZ')).toBe(true)
    })

    it('处理未平仓的买入（忽略）', () => {
      const trades: Trade[] = [
        { date: '2024-01-01', action: 'buy', stock_code: '600000.SH', price: 10.0, shares: 100 },
        { date: '2024-01-05', action: 'sell', stock_code: '600000.SH', price: 12.0, shares: 100 },
        { date: '2024-01-10', action: 'buy', stock_code: '600000.SH', price: 11.0, shares: 100 },
        // 没有对应的卖出
      ]

      const positions = analyzePositions(trades)

      // 只返回已配对的持仓
      expect(positions).toHaveLength(1)
    })

    it('处理空交易列表', () => {
      const positions = analyzePositions([])
      expect(positions).toHaveLength(0)
    })
  })

  describe('calculatePositionStats', () => {
    const positions = [
      {
        stockCode: '600000.SH',
        buyDate: '2024-01-01',
        sellDate: '2024-01-05',
        buyPrice: 10.0,
        sellPrice: 12.0,
        shares: 100,
        holdingDays: 4,
        returnRate: 0.2,
        profit: 200,
      },
      {
        stockCode: '600000.SH',
        buyDate: '2024-01-02',
        sellDate: '2024-01-06',
        buyPrice: 11.0,
        sellPrice: 10.0,
        shares: 100,
        holdingDays: 4,
        returnRate: -0.0909,
        profit: -100,
      },
      {
        stockCode: '000001.SZ',
        buyDate: '2024-01-03',
        sellDate: '2024-01-10',
        buyPrice: 20.0,
        sellPrice: 24.0,
        shares: 50,
        holdingDays: 7,
        returnRate: 0.2,
        profit: 200,
      },
    ]

    it('计算总持仓数', () => {
      const stats = calculatePositionStats(positions)
      expect(stats.totalPositions).toBe(3)
    })

    it('计算盈利和亏损笔数', () => {
      const stats = calculatePositionStats(positions)
      expect(stats.winningPositions).toBe(2)
      expect(stats.losingPositions).toBe(1)
    })

    it('计算胜率', () => {
      const stats = calculatePositionStats(positions)
      expect(stats.winRate).toBeCloseTo(0.6667, 2) // 2/3
    })

    it('计算平均持仓天数', () => {
      const stats = calculatePositionStats(positions)
      expect(stats.avgHoldingDays).toBeCloseTo(5, 0) // (4+4+7)/3 = 5
    })

    it('计算平均收益率', () => {
      const stats = calculatePositionStats(positions)
      // (0.2 + (-0.0909) + 0.2) / 3 ≈ 0.1030
      expect(stats.avgReturn).toBeCloseTo(0.1030, 2)
    })

    it('计算平均盈利率和亏损率', () => {
      const stats = calculatePositionStats(positions)
      // 平均盈利率: (0.2 + 0.2) / 2 = 0.2
      expect(stats.avgWinReturn).toBeCloseTo(0.2, 2)
      // 平均亏损率: -0.0909
      expect(stats.avgLossReturn).toBeCloseTo(-0.0909, 2)
    })

    it('计算最大盈利和亏损', () => {
      const stats = calculatePositionStats(positions)
      expect(stats.maxWinReturn).toBeCloseTo(0.2, 2)
      expect(stats.maxLossReturn).toBeCloseTo(-0.0909, 2)
    })

    it('处理空持仓列表', () => {
      const stats = calculatePositionStats([])
      expect(stats.totalPositions).toBe(0)
      expect(stats.winningPositions).toBe(0)
      expect(stats.losingPositions).toBe(0)
      expect(stats.winRate).toBe(0)
      expect(stats.avgHoldingDays).toBe(0)
      expect(stats.avgReturn).toBe(0)
    })

    it('处理全部盈利的情况', () => {
      const allWinning = [
        {
          stockCode: '600000.SH',
          buyDate: '2024-01-01',
          sellDate: '2024-01-05',
          buyPrice: 10.0,
          sellPrice: 12.0,
          shares: 100,
          holdingDays: 4,
          returnRate: 0.2,
          profit: 200,
        },
      ]

      const stats = calculatePositionStats(allWinning)
      expect(stats.winningPositions).toBe(1)
      expect(stats.losingPositions).toBe(0)
      expect(stats.winRate).toBe(1.0)
      expect(stats.avgLossReturn).toBe(0)
    })
  })

  describe('calculateDrawdown', () => {
    it('计算回撤数据', () => {
      const dailyPortfolio: DailyPortfolio[] = [
        { date: '2024-01-01', value: 100000 },
        { date: '2024-01-02', value: 105000 },
        { date: '2024-01-03', value: 110000 }, // 峰值
        { date: '2024-01-04', value: 105000 }, // 回撤: (105000-110000)/110000 = -4.55%
        { date: '2024-01-05', value: 100000 }, // 回撤: (100000-110000)/110000 = -9.09%
        { date: '2024-01-06', value: 108000 }, // 回撤: (108000-110000)/110000 = -1.82%
        { date: '2024-01-07', value: 115000 }, // 新峰值
      ]

      const drawdowns = calculateDrawdown(dailyPortfolio)

      expect(drawdowns).toHaveLength(7)

      // 第1天：初始值，无回撤
      expect(drawdowns[0].drawdown).toBe(0)

      // 第2-3天：持续上涨，无回撤
      expect(drawdowns[1].drawdown).toBe(0)
      expect(drawdowns[2].drawdown).toBe(0)

      // 第4天：回撤 -4.55%
      expect(drawdowns[3].drawdown).toBeCloseTo(-0.0455, 2)

      // 第5天：最大回撤 -9.09%
      expect(drawdowns[4].drawdown).toBeCloseTo(-0.0909, 2)

      // 第6天：回撤减小
      expect(drawdowns[5].drawdown).toBeCloseTo(-0.0182, 2)

      // 第7天：创新高，回撤归零
      expect(drawdowns[6].drawdown).toBe(0)
    })

    it('处理持续上涨的情况', () => {
      const dailyPortfolio: DailyPortfolio[] = [
        { date: '2024-01-01', value: 100000 },
        { date: '2024-01-02', value: 105000 },
        { date: '2024-01-03', value: 110000 },
        { date: '2024-01-04', value: 115000 },
      ]

      const drawdowns = calculateDrawdown(dailyPortfolio)

      // 持续上涨，无回撤
      drawdowns.forEach(d => {
        expect(d.drawdown).toBe(0)
      })
    })

    it('处理持续下跌的情况', () => {
      const dailyPortfolio: DailyPortfolio[] = [
        { date: '2024-01-01', value: 100000 },
        { date: '2024-01-02', value: 95000 },
        { date: '2024-01-03', value: 90000 },
        { date: '2024-01-04', value: 85000 },
      ]

      const drawdowns = calculateDrawdown(dailyPortfolio)

      // 第1天：峰值
      expect(drawdowns[0].drawdown).toBe(0)

      // 第2天：-5%
      expect(drawdowns[1].drawdown).toBeCloseTo(-0.05, 2)

      // 第3天：-10%
      expect(drawdowns[2].drawdown).toBeCloseTo(-0.10, 2)

      // 第4天：-15%
      expect(drawdowns[3].drawdown).toBeCloseTo(-0.15, 2)
    })

    it('处理空列表', () => {
      const drawdowns = calculateDrawdown([])
      expect(drawdowns).toHaveLength(0)
    })

    it('处理单个数据点', () => {
      const dailyPortfolio: DailyPortfolio[] = [
        { date: '2024-01-01', value: 100000 },
      ]

      const drawdowns = calculateDrawdown(dailyPortfolio)

      expect(drawdowns).toHaveLength(1)
      expect(drawdowns[0].drawdown).toBe(0)
    })
  })
})
