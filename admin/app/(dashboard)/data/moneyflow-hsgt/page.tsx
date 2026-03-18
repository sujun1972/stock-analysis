'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DateRangePicker } from '@/components/common/DatePicker'
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

export default function MoneyflowHsgtPage() {
  const [data, setData] = useState<MoneyflowData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
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
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      params.append('limit', pageSize.toString())
      params.append('offset', ((page - 1) * pageSize).toString())

      // 获取资金流向数据
      const response = await apiClient.get(`/api/moneyflow-hsgt?${params.toString()}`)

      console.log('Moneyflow API Response:', response)

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
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

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
    const headers = ['交易日期', '沪股通(百万)', '深股通(百万)', '北向资金(百万)', '港股通沪(百万)', '港股通深(百万)', '南向资金(百万)']
    const csvContent = [
      headers.join(','),
      ...data.map(item => [
        item.trade_date,
        item.hgt,
        item.sgt,
        item.north_money,
        item.ggt_ss,
        item.ggt_sz,
        item.south_money
      ].join(','))
    ].join('\n')

    // 创建下载
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `moneyflow_hsgt_${startDate || 'all'}_${endDate || 'latest'}.csv`
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
      header: '交易日期',
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
      header: '沪股通',
      accessor: (item) => (
        <span className={`font-medium ${item.hgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.hgt >= 0 ? '+' : ''}{formatNumber(item.hgt, 2)}
        </span>
      )
    },
    {
      key: 'sgt',
      header: '深股通',
      accessor: (item) => (
        <span className={`font-medium ${item.sgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.sgt >= 0 ? '+' : ''}{formatNumber(item.sgt, 2)}
        </span>
      )
    },
    {
      key: 'north_money',
      header: '北向资金合计',
      accessor: (item) => (
        <span className={`font-semibold text-lg ${item.north_money >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.north_money >= 0 ? '+' : ''}{formatNumber(item.north_money, 2)}
        </span>
      )
    },
    {
      key: 'ggt_ss',
      header: '港股通（沪）',
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatNumber(item.ggt_ss, 2)}
        </span>
      )
    },
    {
      key: 'ggt_sz',
      header: '港股通（深）',
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatNumber(item.ggt_sz, 2)}
        </span>
      )
    },
    {
      key: 'south_money',
      header: '南向资金合计',
      accessor: (item) => (
        <span className="text-gray-600 dark:text-gray-400">
          {formatNumber(item.south_money, 2)}
        </span>
      )
    }
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((item: MoneyflowData) => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-medium text-lg">
          {(() => {
            const dateStr = item.trade_date
            if (dateStr && dateStr.length === 8 && !dateStr.includes('-')) {
              const formatted = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
              return formatDate(formatted)
            }
            return formatDate(dateStr)
          })()}
        </div>
        <div className={`font-bold text-xl ${item.north_money >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
          {item.north_money >= 0 ? '+' : ''}{formatNumber(item.north_money, 2)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">沪股通：</span>
          <span className={`font-medium ml-1 ${item.hgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
            {item.hgt >= 0 ? '+' : ''}{formatNumber(item.hgt, 2)}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">深股通：</span>
          <span className={`font-medium ml-1 ${item.sgt >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
            {item.sgt >= 0 ? '+' : ''}{formatNumber(item.sgt, 2)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs text-gray-500 dark:text-gray-400">
        <div>港股通（沪）：{formatNumber(item.ggt_ss, 2)}</div>
        <div>港股通（深）：{formatNumber(item.ggt_sz, 2)}</div>
      </div>
    </div>
  ), [])

  // 准备图表数据
  const chartData = useMemo(() => {
    return [...data].reverse().map(item => ({
      date: item.trade_date.slice(4), // 只显示MMDD
      north: item.north_money,
      south: item.south_money,
      hgt: item.hgt,
      sgt: item.sgt,
      net: item.north_money - item.south_money
    }))
  }, [data])

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
                  {formatNumber(statistics.avg_north, 2)}
                </p>
                <p className="text-xs text-gray-500 mt-1">百万元</p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">累计净流入</p>
                <p className={`text-2xl font-semibold mt-1 ${statistics.total_north >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {formatNumber(statistics.total_north / 1000, 2)}
                </p>
                <p className="text-xs text-gray-500 mt-1">十亿元</p>
              </div>
              <Activity className="h-8 w-8 text-green-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">最大流入</p>
                <p className="text-2xl font-semibold mt-1 text-red-600 dark:text-red-400">
                  {formatNumber(statistics.max_north, 2)}
                </p>
                <p className="text-xs text-gray-500 mt-1">百万元</p>
              </div>
              <ArrowUpRight className="h-8 w-8 text-red-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">最大流出</p>
                <p className="text-2xl font-semibold mt-1 text-green-600 dark:text-green-400">
                  {formatNumber(statistics.min_north, 2)}
                </p>
                <p className="text-xs text-gray-500 mt-1">百万元</p>
              </div>
              <ArrowDownRight className="h-8 w-8 text-green-500" />
            </div>
          </Card>
        </div>
      )}

      {/* 图表 */}
      {chartData.length > 0 && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">资金流向趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip formatter={(value: any) => formatNumber(value, 2)} />
              <Legend />
              <Area
                type="monotone"
                dataKey="north"
                name="北向资金"
                stroke="#ef4444"
                fill="#ef4444"
                fillOpacity={0.3}
              />
              <Area
                type="monotone"
                dataKey="south"
                name="南向资金"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* 筛选器 */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <DateRangePicker
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
            className="w-full sm:w-auto"
          />

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(1) // 重置到第一页
              loadData()
            }}
          >
            查询
          </Button>
        </div>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          error={error}
          emptyMessage="暂无资金流向数据"
          mobileCard={mobileCard}
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
      </Card>
    </div>
  )
}