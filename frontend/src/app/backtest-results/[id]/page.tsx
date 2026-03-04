/**
 * 回测结果详情页面
 *
 * 功能:
 * - 展示单个回测记录的完整详情（策略信息、绩效指标、图表、交易记录）
 * - 使用与回测配置页面相同的垂直布局，提供一致的用户体验
 * - 支持URL分享和收藏
 *
 * 路由: /backtest-results/[id]
 *
 * 设计说明:
 * - 从模态框改为独立页面，提供更好的空间利用和可分享性
 * - 复用 BacktestResultView 和 TradesTable 组件保持一致性
 * - 采用全页面布局，适合展示大量数据（图表、交易记录等）
 */

'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import BacktestResultView, { TradesTable } from '@/components/backtest/BacktestResultView'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import apiClient from '@/lib/api-client'

interface BacktestRecord {
  id: number
  execution_type: string
  status: string
  strategy: {
    name: string
    display_name?: string
    source_type?: string
    description?: string
  }
  metrics: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    sortino_ratio: number
    calmar_ratio: number
    max_drawdown: number
    volatility: number
    win_rate: number
    profit_factor: number
    total_trades: number
  }
  execution_params: {
    stock_pool: string[]
    start_date: string
    end_date: string
    initial_capital: number
  }
  result: {
    equity_curve: Array<{
      date: string
      cash: number
      holdings: number
      total: number
    }>
    trades: Array<{
      date: string
      stock_code: string
      stock_name: string
      action: string
      price: number
      shares: number
      amount: number
      entry_reason?: string
      exit_reason?: string
      exit_trigger?: string
      cash_after: number
      holdings_value_after: number
      total_value_after: number
    }>
    stock_charts: Record<string, any>
  }
  execution_duration_ms?: number
  started_at: string
  completed_at?: string
}

export default function BacktestResultPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [record, setRecord] = useState<BacktestRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 从后端加载回测详情数据
  useEffect(() => {
    const fetchBacktestDetail = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.get(`/api/backtest-history/${id}`)
        // 后端返回格式: { success: true, data: {...} }
        // apiClient.get() 已经返回了 response.data，所以这里需要再访问 .data
        setRecord(response.data)
      } catch (err: any) {
        console.error('获取回测详情失败:', err)
        setError(err.response?.data?.detail || '获取回测详情失败，请稍后重试')
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchBacktestDetail()
    }
  }, [id])

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </ProtectedRoute>
    )
  }

  if (error || !record) {
    return (
      <ProtectedRoute>
        <div className="container-custom py-8">
          <Card className="max-w-2xl mx-auto">
            <CardContent className="py-12 text-center">
              <p className="text-red-600">{error || '回测记录不存在'}</p>
            </CardContent>
          </Card>
        </div>
      </ProtectedRoute>
    )
  }

  /**
   * 转换数据格式
   * 将后端返回的 BacktestRecord 转换为 BacktestResultView 组件所需的格式
   * 这样可以复用回测配置页面的结果展示组件
   */
  const resultForView = record ? {
    strategy_info: {
      display_name: record.strategy?.display_name || record.strategy?.name,
      name: record.strategy?.name,
      source_type: record.strategy?.source_type,
      description: record.strategy?.description
    },
    backtest_params: {
      stock_pool: record.execution_params?.stock_pool,
      start_date: record.execution_params?.start_date,
      end_date: record.execution_params?.end_date,
      initial_capital: record.execution_params?.initial_capital
    },
    metrics: record.metrics,
    equity_curve: record.result?.equity_curve,
    trades: record.result?.trades,
    stock_charts: record.result?.stock_charts
  } : null

  return (
    <ProtectedRoute>
      <div className="container-custom py-8">
        {/* 标题 */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            回测详情
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            {record.strategy?.display_name || record.strategy?.name} -
            {record.execution_params?.start_date} ~ {record.execution_params?.end_date}
          </p>
        </div>

        {/* 回测参数卡片 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>回测参数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">股票池:</span>
                <span className="ml-2 font-medium">
                  {record.execution_params?.stock_pool?.length || 0} 只股票
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">初始资金:</span>
                <span className="ml-2 font-medium">
                  ¥{(record.execution_params?.initial_capital || 0).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">回测区间:</span>
                <span className="ml-2 font-medium">
                  {record.execution_params?.start_date} ~ {record.execution_params?.end_date}
                </span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">执行时长:</span>
                <span className="ml-2 font-medium">
                  {record.execution_duration_ms ?
                    `${(record.execution_duration_ms / 1000).toFixed(2)}秒` :
                    '-'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 回测结果 - 使用与回测页面相同的布局 */}
        {resultForView && (
          <>
            <BacktestResultView result={resultForView} />

            {/* 交易明细表格 */}
            {resultForView.trades && resultForView.trades.length > 0 && (
              <div className="mt-6">
                <TradesTable result={resultForView} />
              </div>
            )}
          </>
        )}
      </div>
    </ProtectedRoute>
  )
}
