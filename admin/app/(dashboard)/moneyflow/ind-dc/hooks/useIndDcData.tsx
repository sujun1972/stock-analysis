'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useDataPage } from '@/hooks/useDataPage'
import { moneyflowApi } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { BarChart3, Activity, TrendingUp, DollarSign } from 'lucide-react'
import type { StatisticsCardItem } from '@/components/common/StatisticsCards'
import { type MoneyflowIndDcData, type Statistics, pctColor } from '../types'

export function useIndDcData() {
  // 查询筛选状态（页面个性化）
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [contentType, setContentType] = useState<string>('all')

  // TOP 板块图表数据（独立加载，不走 useDataPage）
  const [topSectors, setTopSectors] = useState<MoneyflowIndDcData[]>([])

  const dp = useDataPage<MoneyflowIndDcData, Statistics>({
    apiCall: (params) => moneyflowApi.getMoneyflowIndDc(params),
    taskName: 'tasks.sync_moneyflow_ind_dc',
    bulkOps: {
      tableKey: 'moneyflow_ind_dc',
      syncFn: (params) => axiosInstance.post('/api/moneyflow-ind-dc/sync-full-history', null, { params }),
      taskName: 'tasks.sync_moneyflow_ind_dc_full_history',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (contentType && contentType !== 'all') params.content_type = contentType
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
  })

  // 独立加载 TOP 板块
  const loadTopSectors = useCallback(async () => {
    try {
      const response = await moneyflowApi.getTopMoneyflowIndustries({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopSectors(Array.isArray(response.data) ? response.data : response.data.items || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }, [])

  useEffect(() => {
    loadTopSectors().catch(() => {})
  }, [loadTopSectors])

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '板块数',
        value: `${s.sector_count ?? 0}个`,
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '主力资金均值(亿)',
        value: <span className={pctColor(s.avg_net_amount)}>{(s.avg_net_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_net_amount ?? 0).toFixed(2)}</span>,
        icon: Activity,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大净流入(亿)',
        value: <span className="text-red-600">+{(s.max_net_amount ?? 0).toFixed(2)}</span>,
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '超大单均值(亿)',
        value: <span className={pctColor(s.avg_buy_elg_amount)}>{(s.avg_buy_elg_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_buy_elg_amount ?? 0).toFixed(2)}</span>,
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 图表数据（TOP 20）
  const chartData = useMemo(() => topSectors.map(item => ({
    name: item.name || item.ts_code,
    主力净流入: item.net_amount ?? 0,
    超大单: item.buy_elg_amount ?? 0,
    大单: item.buy_lg_amount ?? 0,
  })), [topSectors])

  return {
    // 筛选状态
    tradeDate,
    setTradeDate,
    contentType,
    setContentType,
    // useDataPage 实例
    dp,
    // 统计卡片
    statsCards,
    // 图表数据
    chartData,
    // 用于同步完成后刷新
    loadTopSectors,
  }
}
