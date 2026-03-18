/**
 * @file 沪深港通资金流向页面
 * @description 展示沪深港通每日资金流向数据，包括北向资金（沪股通+深股通）和南向资金（港股通）
 * @features
 * - 统计卡片展示：北向资金均值、累计净流入、最大流入、南向最大流出
 * - 趋势图表：展示北向和南向资金流向趋势
 * - 数据筛选：支持按日期范围筛选
 * - 数据同步：支持手动同步最新数据
 * - 数据导出：导出CSV格式数据（单位：亿元）
 * - 响应式设计：桌面端表格视图，移动端卡片视图
 */

'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { apiClient } from '@/lib/api-client'
import { toast } from '@/hooks/use-toast'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  RefreshCw,
  Download,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { formatNumber, formatDate } from '@/lib/utils'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'

interface MoneyflowData {
  trade_date: string
  ggt_ss: number      // 港股通（上海）
  ggt_sz: number      // 港股通（深圳）
  hgt: number         // 沪股通
  sgt: number         // 深股通
  north_money: number // 北向资金
  south_money: number // 南向资金
  created_at?: string
  updated_at?: string
}

interface Statistics {
  avg_north: number
  max_north: number
  min_north: number
  total_north: number
  avg_south: number
  max_south: number
  min_south: number
  total_south: number
  latest_date: string
  earliest_date: string
  count: number
}

/**
 * 格式化金额为亿元
 * @param value 百万元为单位的金额
 * @param decimals 保留小数位数，默认2位
 * @returns 格式化后的字符串（亿元）
 */
const formatToYi = (value: number, decimals: number = 2): string => {
  return formatNumber(value / 100, decimals)
}

export default function MoneyflowHsgtPage() {
  const [data, setData] = useState<MoneyflowData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [refreshing, setRefreshing] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // 构建查询参数
      const params = new URLSearchParams()
      if (startDate) {
        const startStr = startDate.toISOString().split('T')[0].replace(/-/g, '')
        params.append('start_date', startStr)
      }
      if (endDate) {
        const endStr = endDate.toISOString().split('T')[0].replace(/-/g, '')
        params.append('end_date', endStr)
      }
      params.append('limit', pageSize.toString())
      params.append('offset', ((page - 1) * pageSize).toString())

      // 获取资金流向数据
      const response = await apiClient.get(`/api/moneyflow-hsgt?${params.toString()}`)

      if (response.code === 200) {
        const items = response.data?.items || []
        const stats = response.data?.statistics || null
        const totalCount = response.data?.total || 0

        setData(items)
        setStatistics(stats)
        setTotal(totalCount)
      } else {
        throw new Error(response.message || '加载数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast({
        title: "加载失败",
        description: err.message || '无法加载资金流向数据',
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, page, pageSize])

  // 同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params = new URLSearchParams()
      if (startDate) {
        const startStr = startDate.toISOString().split('T')[0].replace(/-/g, '')
        params.append('start_date', startStr)
      }
      if (endDate) {
        const endStr = endDate.toISOString().split('T')[0].replace(/-/g, '')
        params.append('end_date', endStr)
      }

      const response = await apiClient.post(`/api/moneyflow-hsgt/sync?${params.toString()}`)

      if (response.code === 200) {
        toast({
          title: "同步成功",
          description: response.message || "资金流向数据同步成功",
          variant: "default"
        })

        // 刷新数据
        await loadData()
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast({
        title: "同步失败",
        description: err.message || '无法同步数据',
        variant: "destructive"
      })
    } finally {
      setSyncing(false)
    }
  }

  // 导出数据
  const handleExport = () => {
    // 将数据转换为CSV格式
    const headers = ['交易日期', '沪股通(亿元)', '深股通(亿元)', '北向资金(亿元)', '港股通沪(亿元)', '港股通深(亿元)', '南向资金(亿元)']
    const csvContent = [
      headers.join(','),
      ...data.map(item => [
        item.trade_date,
        formatToYi(item.hgt),
        formatToYi(item.sgt),
        formatToYi(item.north_money),
        formatToYi(item.ggt_ss),
        formatToYi(item.ggt_sz),
        formatToYi(item.south_money)
      ].join(','))
    ].join('\n')

    // 创建下载
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const startStr = startDate ? startDate.toISOString().split('T')[0] : 'all'
    const endStr = endDate ? endDate.toISOString().split('T')[0] : 'latest'
    a.download = `moneyflow_hsgt_${startStr}_${endStr}.csv`
    a.click()
    window.URL.revokeObjectURL(url)

    toast({
      title: "导出成功",
      description: `已导出 ${data.length} 条数据`,
      variant: "default"
    })
  }

  useEffect(() => {
    loadData()
  }, [loadData])

  // 定义表格列
  const columns: Column<MoneyflowData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (item) => {
        const dateStr = item.trade_date
        if (dateStr && dateStr.length === 8 && !dateStr.includes('-')) {
          // YYYYMMDD格式转换为YYYY-MM-DD
          const formatted = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
          return formatDate(formatted)
        }
        return formatDate(dateStr)
      }
    },
    {
      key: 'hgt',
      header: (
        <>
          <span className="sm:hidden">沪</span>
          <span className="hidden sm:inline">沪股通(亿)</span>
        </>
      ),
      accessor: (item) => (
        <span className={`font-medium ${item.hgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.hgt >= 0 ? '+' : ''}{formatToYi(item.hgt)}
        </span>
      )
    },
    {
      key: 'sgt',
      header: (
        <>
          <span className="sm:hidden">深</span>
          <span className="hidden sm:inline">深股通(亿)</span>
        </>
      ),
      accessor: (item) => (
        <span className={`font-medium ${item.sgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.sgt >= 0 ? '+' : ''}{formatToYi(item.sgt)}
        </span>
      )
    },
    {
      key: 'north_money',
      header: (
        <>
          <span className="sm:hidden">北向</span>
          <span className="hidden sm:inline">北向合计(亿)</span>
        </>
      ),
      accessor: (item) => (
        <span className={`font-semibold sm:text-lg ${item.north_money >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.north_money >= 0 ? '+' : ''}{formatToYi(item.north_money)}
        </span>
      )
    },
    {
      key: 'ggt_ss',
      header: '港沪(亿)',
      className: 'hidden md:table-cell',
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatToYi(item.ggt_ss)}
        </span>
      )
    },
    {
      key: 'ggt_sz',
      header: '港深(亿)',
      className: 'hidden md:table-cell',
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatToYi(item.ggt_sz)}
        </span>
      )
    },
    {
      key: 'south_money',
      header: (
        <>
          <span className="sm:hidden">南向</span>
          <span className="hidden sm:inline">南向合计(亿)</span>
        </>
      ),
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatToYi(item.south_money)}
        </span>
      )
    }
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((item: MoneyflowData) => (
    <div className="space-y-2">
      {/* 日期 */}
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">交易日期</span>
        <span className="font-medium">
          {(() => {
            const dateStr = item.trade_date
            if (dateStr && dateStr.length === 8 && !dateStr.includes('-')) {
              const formatted = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
              return formatDate(formatted)
            }
            return formatDate(dateStr)
          })()}
        </span>
      </div>

      {/* 北向合计 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">北向合计</span>
        <span className={`font-bold text-lg ${item.north_money >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.north_money >= 0 ? '+' : ''}{formatToYi(item.north_money)}亿
        </span>
      </div>

      {/* 沪股通 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">沪股通</span>
        <span className={`font-medium ${item.hgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.hgt >= 0 ? '+' : ''}{formatToYi(item.hgt)}亿
        </span>
      </div>

      {/* 深股通 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">深股通</span>
        <span className={`font-medium ${item.sgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.sgt >= 0 ? '+' : ''}{formatToYi(item.sgt)}亿
        </span>
      </div>

      {/* 分隔线 */}
      <div className="border-t border-gray-100 dark:border-gray-800"></div>

      {/* 南向合计 */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">南向合计</span>
        <span className="font-medium text-gray-700 dark:text-gray-300">
          {formatToYi(item.south_money)}亿
        </span>
      </div>

      {/* 港股通(沪) */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500 dark:text-gray-500">港股通(沪)</span>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatToYi(item.ggt_ss)}亿
        </span>
      </div>

      {/* 港股通(深) */}
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500 dark:text-gray-500">港股通(深)</span>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatToYi(item.ggt_sz)}亿
        </span>
      </div>
    </div>
  ), [])

  // 准备图表数据
  const chartData = useMemo(() => {
    return [...data].reverse().map(item => ({
      date: item.trade_date.slice(4), // 只显示MMDD
      north: item.north_money / 100, // 转换为亿元
      south: item.south_money / 100,
      hgt: item.hgt / 100,
      sgt: item.sgt / 100,
      net: (item.north_money - item.south_money) / 100
    }))
  }, [data])

  // 图表 Tooltip 格式化
  const chartTooltipFormatter = (value: any) => {
    return `${value.toFixed(2)} 亿元`
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="沪深港通资金流向"
        description="查看沪深港通每日资金流向数据"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={data.length === 0}
            >
              <Download className="h-4 w-4 mr-1" />
              导出
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleSync}
              disabled={syncing}
            >
              {syncing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  同步数据
                </>
              )}
            </Button>
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">北向资金均值</p>
                <p className={`text-2xl font-semibold mt-1 ${statistics.avg_north >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {formatToYi(statistics.avg_north)}
                </p>
                <p className="text-xs text-gray-500 mt-1">亿元</p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">累计净流入</p>
                <p className={`text-2xl font-semibold mt-1 ${statistics.total_north >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {formatToYi(statistics.total_north)}
                </p>
                <p className="text-xs text-gray-500 mt-1">亿元</p>
              </div>
              <Activity className="h-8 w-8 text-green-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">北向最大流入</p>
                <p className="text-2xl font-semibold mt-1 text-red-600 dark:text-red-400">
                  {formatToYi(statistics.max_north)}
                </p>
                <p className="text-xs text-gray-500 mt-1">亿元</p>
              </div>
              <ArrowUpRight className="h-8 w-8 text-red-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">南向最大流出</p>
                <p className="text-2xl font-semibold mt-1 text-green-600 dark:text-green-400">
                  {formatToYi(statistics.max_south)}
                </p>
                <p className="text-xs text-gray-500 mt-1">亿元</p>
              </div>
              <ArrowDownRight className="h-8 w-8 text-green-500" />
            </div>
          </Card>
        </div>
      )}

      {/* 图表 */}
      {chartData.length > 0 && (
        <Card className="p-4 overflow-hidden">
          <h3 className="text-lg font-semibold mb-4">资金流向趋势</h3>
          <div className="w-full overflow-x-auto pb-4">
            <ResponsiveContainer width="100%" height={300} minWidth={300}>
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval="preserveStartEnd"
                />
                <YAxis />
                <Tooltip formatter={chartTooltipFormatter} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Area
                  type="monotone"
                  dataKey="north"
                  name="北向(亿)"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.3}
                />
                <Area
                  type="monotone"
                  dataKey="south"
                  name="南向(亿)"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 筛选器 - 优化布局对齐 */}
      <Card className="p-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:flex-1">
            <span className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">开始日期</span>
            <DatePicker
              date={startDate}
              onDateChange={setStartDate}
              placeholder="选择开始日期"
              className="w-full sm:w-[200px]"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:flex-1">
            <span className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">结束日期</span>
            <DatePicker
              date={endDate}
              onDateChange={setEndDate}
              placeholder="选择结束日期"
              className="w-full sm:w-[200px]"
            />
          </div>

          <Button
            variant="outline"
            onClick={() => {
              setPage(1) // 重置到第一页
              loadData()
            }}
            className="w-full sm:w-auto"
          >
            查询
          </Button>
        </div>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="sm:hidden">
          {/* 移动端视图 - 卡片列表 */}
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">资金流向数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>
          {loading && (
            <div className="p-8 text-center">
              <div className="flex flex-col items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                <span className="text-sm text-muted-foreground">加载中...</span>
              </div>
            </div>
          )}
          {error && (
            <div className="p-8 text-center">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
          {!loading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无资金流向数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!loading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  第 {page} / {Math.ceil(total / pageSize)} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无资金流向数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1) // 重置到第一页
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>
    </div>
  )
}