/**
 * 分时数据聚合工具
 *
 * 功能：将1分钟K线数据聚合为更大周期（5/15/30/60分钟）
 * 原理：OHLC聚合规则
 *   - Open: 取周期内第一条数据的开盘价
 *   - High: 取周期内最高价
 *   - Low: 取周期内最低价
 *   - Close: 取周期内最后一条数据的收盘价
 *   - Volume: 周期内成交量求和
 *   - Amount: 周期内成交额求和
 */

import type { MinuteData } from '@/types'

export type MinutePeriod = '1' | '5' | '15' | '30' | '60'

/**
 * 将1分钟K线数据聚合为指定周期
 *
 * @param minuteData - 1分钟K线数据数组（必须是1分钟数据）
 * @param targetPeriod - 目标周期（'1' | '5' | '15' | '30' | '60'）
 * @returns 聚合后的K线数据
 */
export function aggregateMinuteData(
  minuteData: MinuteData[],
  targetPeriod: MinutePeriod
): MinuteData[] {
  // 如果目标周期是1分钟，直接返回原数据
  if (targetPeriod === '1') {
    return minuteData
  }

  // 如果没有数据，返回空数组
  if (!minuteData || minuteData.length === 0) {
    return []
  }

  const period = parseInt(targetPeriod)
  const result: MinuteData[] = []

  // 按周期分组并聚合
  for (let i = 0; i < minuteData.length; i += period) {
    const chunk = minuteData.slice(i, i + period)

    if (chunk.length === 0) continue

    // 聚合OHLC数据
    const aggregated: MinuteData = {
      trade_time: chunk[0].trade_time, // 使用周期内第一条数据的时间
      open: chunk[0].open,              // 第一条的开盘价
      high: Math.max(...chunk.map(d => d.high)), // 最高价
      low: Math.min(...chunk.map(d => d.low)),   // 最低价
      close: chunk[chunk.length - 1].close,      // 最后一条的收盘价
      volume: chunk.reduce((sum, d) => sum + d.volume, 0), // 成交量求和
    }

    // 可选字段聚合
    if (chunk[0].amount !== undefined) {
      aggregated.amount = chunk.reduce((sum, d) => sum + (d.amount || 0), 0)
    }

    // 计算涨跌幅（基于周期内的开盘和收盘）
    if (aggregated.open !== 0) {
      aggregated.pct_change = ((aggregated.close - aggregated.open) / aggregated.open) * 100
      aggregated.change_amount = aggregated.close - aggregated.open
    }

    result.push(aggregated)
  }

  return result
}

/**
 * 验证数据是否为1分钟数据
 *
 * @param data - 待验证的数据
 * @returns 是否为1分钟数据
 */
export function isOneMinuteData(data: MinuteData[]): boolean {
  if (!data || data.length < 2) return true // 数据太少，无法判断

  // 检查前10条数据的时间间隔
  const maxCheck = Math.min(10, data.length - 1)

  for (let i = 0; i < maxCheck; i++) {
    const time1 = new Date(data[i].trade_time).getTime()
    const time2 = new Date(data[i + 1].trade_time).getTime()
    const diffMinutes = Math.abs(time2 - time1) / (1000 * 60)

    // 允许1-2分钟的误差（考虑到可能的数据缺失）
    if (diffMinutes > 2) {
      return false
    }
  }

  return true
}

/**
 * 获取期望的数据条数
 *
 * @param period - 周期（分钟）
 * @returns 一个交易日的期望记录数
 */
export function getExpectedRecordCount(period: MinutePeriod): number {
  const tradingMinutes = 240 // A股交易时间：4小时 = 240分钟

  const periodNum = parseInt(period)
  return Math.floor(tradingMinutes / periodNum)
}

/**
 * 格式化周期显示
 *
 * @param period - 周期值
 * @returns 格式化后的周期文本
 */
export function formatPeriodLabel(period: MinutePeriod): string {
  const labels: Record<MinutePeriod, string> = {
    '1': '1分钟',
    '5': '5分钟',
    '15': '15分钟',
    '30': '30分钟',
    '60': '60分钟'
  }
  return labels[period] || `${period}分钟`
}

/**
 * 计算聚合后的数据完整度
 *
 * @param aggregatedData - 聚合后的数据
 * @param targetPeriod - 目标周期
 * @returns 完整度百分比（0-100）
 */
export function calculateCompleteness(
  aggregatedData: MinuteData[],
  targetPeriod: MinutePeriod
): number {
  const expected = getExpectedRecordCount(targetPeriod)
  const actual = aggregatedData.length

  return Math.min(100, (actual / expected) * 100)
}
