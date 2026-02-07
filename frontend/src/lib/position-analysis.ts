import type { Trade } from './three-layer-types'

/**
 * 持仓记录（配对的买入-卖出）
 */
export interface PositionRecord {
  stockCode: string
  buyDate: string
  sellDate: string
  buyPrice: number
  sellPrice: number
  shares: number
  holdingDays: number
  returnRate: number
  profit: number
}

/**
 * 从交易记录中提取配对的持仓记录
 * 将买入和卖出交易配对，计算每笔持仓的收益率和持仓时间
 */
export function analyzePositions(trades: Trade[]): PositionRecord[] {
  const positions: PositionRecord[] = []
  const openPositions: Map<string, Trade[]> = new Map()

  // 按股票代码分组，找到配对的买入-卖出
  trades.forEach(trade => {
    const { stock_code, action } = trade

    if (action === 'buy') {
      // 买入：添加到开仓记录
      if (!openPositions.has(stock_code)) {
        openPositions.set(stock_code, [])
      }
      openPositions.get(stock_code)!.push(trade)
    } else if (action === 'sell') {
      // 卖出：与最早的买入配对（FIFO）
      const buys = openPositions.get(stock_code)
      if (buys && buys.length > 0) {
        const buyTrade = buys.shift()! // 取出最早的买入

        // 计算持仓时间（天数）
        const buyDate = new Date(buyTrade.date)
        const sellDate = new Date(trade.date)
        const holdingDays = Math.floor((sellDate.getTime() - buyDate.getTime()) / (1000 * 60 * 60 * 24))

        // 计算收益率
        const returnRate = (trade.price - buyTrade.price) / buyTrade.price

        // 计算盈亏金额
        const profit = (trade.price - buyTrade.price) * trade.shares

        positions.push({
          stockCode: stock_code,
          buyDate: buyTrade.date,
          sellDate: trade.date,
          buyPrice: buyTrade.price,
          sellPrice: trade.price,
          shares: trade.shares,
          holdingDays,
          returnRate,
          profit
        })
      }
    }
  })

  return positions
}

/**
 * 计算持仓统计数据
 */
export interface PositionStats {
  totalPositions: number
  winningPositions: number
  losingPositions: number
  winRate: number
  avgHoldingDays: number
  avgReturn: number
  avgWinReturn: number
  avgLossReturn: number
  maxWinReturn: number
  maxLossReturn: number
  totalProfit: number
}

export function calculatePositionStats(positions: PositionRecord[]): PositionStats {
  if (positions.length === 0) {
    return {
      totalPositions: 0,
      winningPositions: 0,
      losingPositions: 0,
      winRate: 0,
      avgHoldingDays: 0,
      avgReturn: 0,
      avgWinReturn: 0,
      avgLossReturn: 0,
      maxWinReturn: 0,
      maxLossReturn: 0,
      totalProfit: 0
    }
  }

  const winningPositions = positions.filter(p => p.returnRate > 0)
  const losingPositions = positions.filter(p => p.returnRate <= 0)

  const totalHoldingDays = positions.reduce((sum, p) => sum + p.holdingDays, 0)
  const totalReturn = positions.reduce((sum, p) => sum + p.returnRate, 0)
  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0)

  const avgWinReturn = winningPositions.length > 0
    ? winningPositions.reduce((sum, p) => sum + p.returnRate, 0) / winningPositions.length
    : 0

  const avgLossReturn = losingPositions.length > 0
    ? losingPositions.reduce((sum, p) => sum + p.returnRate, 0) / losingPositions.length
    : 0

  const maxWinReturn = winningPositions.length > 0
    ? Math.max(...winningPositions.map(p => p.returnRate))
    : 0

  const maxLossReturn = losingPositions.length > 0
    ? Math.min(...losingPositions.map(p => p.returnRate))
    : 0

  return {
    totalPositions: positions.length,
    winningPositions: winningPositions.length,
    losingPositions: losingPositions.length,
    winRate: winningPositions.length / positions.length,
    avgHoldingDays: totalHoldingDays / positions.length,
    avgReturn: totalReturn / positions.length,
    avgWinReturn,
    avgLossReturn,
    maxWinReturn,
    maxLossReturn,
    totalProfit
  }
}

/**
 * 计算回撤数据
 */
export interface DrawdownPoint {
  date: string
  drawdown: number
}

export function calculateDrawdown(dailyPortfolio: Array<{ date: string; value: number }>): DrawdownPoint[] {
  const drawdowns: DrawdownPoint[] = []
  let peak = dailyPortfolio[0]?.value || 0

  dailyPortfolio.forEach(point => {
    // 更新峰值
    if (point.value > peak) {
      peak = point.value
    }

    // 计算回撤
    const drawdown = (point.value - peak) / peak

    drawdowns.push({
      date: point.date,
      drawdown
    })
  })

  return drawdowns
}
