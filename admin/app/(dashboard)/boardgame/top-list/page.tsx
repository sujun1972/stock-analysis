'use client'

import { useState, useEffect } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { topListApi, type TopListItem, type TopListStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { TrendingUp, TrendingDown, BarChart3, ListFilter } from 'lucide-react'

export default function TopListPage() {
  const [data, setData] = useState<TopListItem[]>([])
  const [statistics, setStatistics] = useState<TopListStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const { addTask, triggerPoll } = useTaskStore()

  useEffect(() => {
    loadData().catch(() => {})
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const params = {
        start_date: startDate?.toISOString().split('T')[0],
        end_date: endDate?.toISOString().split('T')[0],
        ts_code: tsCode || undefined,
        limit: 30
      }

      const [dataResponse, statsResponse] = await Promise.all([
        topListApi.getTopList(params),
        topListApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSync = async () => {
    try {
      const response = await topListApi.syncAsync({
        trade_date: startDate?.toISOString().split('T')[0],
        ts_code: tsCode || undefined
      })

      if (response.code === 200 && response.data) {
        addTask({
          taskId: response.data.celery_task_id,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        triggerPoll()
        toast.success(response.message || '同步任务已提交')

        setTimeout(() => {
          loadData().catch(() => {})
        }, 3000)
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (error: any) {
      toast.error(error.message || '提交同步任务失败')
    }
  }

  const columns: Column<TopListItem>[] = [
    {
      header: '交易日期',
      accessor: (row) => row.trade_date || '-',
      className: 'w-28'
    },
    {
      header: '股票代码',
      accessor: (row) => row.ts_code || '-',
      className: 'w-28'
    },
    {
      header: '股票名称',
      accessor: (row) => row.name || '-',
      className: 'w-24'
    },
    {
      header: '收盘价',
      accessor: (row) => row.close !== null ? row.close.toFixed(2) : '-',
      className: 'text-right w-24'
    },
    {
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null) return '-'
        const value = row.pct_change
        return (
          <span className={value >= 0 ? 'text-red-600' : 'text-green-600'}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}%
          </span>
        )
      },
      className: 'text-right w-24'
    },
    {
      header: '换手率%',
      accessor: (row) => row.turnover_rate !== null ? row.turnover_rate.toFixed(2) + '%' : '-',
      className: 'text-right w-24'
    },
    {
      header: '总成交额(万)',
      accessor: (row) => row.amount !== null ? row.amount.toFixed(2) : '-',
      className: 'text-right w-32'
    },
    {
      header: '龙虎榜净买入(万)',
      accessor: (row) => {
        if (row.net_amount === null) return '-'
        const value = row.net_amount
        return (
          <span className={value >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}
          </span>
        )
      },
      className: 'text-right w-36'
    },
    {
      header: '龙虎榜成交额(万)',
      accessor: (row) => row.l_amount !== null ? row.l_amount.toFixed(2) : '-',
      className: 'text-right w-36'
    },
    {
      header: '上榜理由',
      accessor: (row) => (
        <div className="max-w-xs truncate" title={row.reason || '-'}>
          {row.reason || '-'}
        </div>
      ),
      className: 'w-64'
    }
  ]

  // 移动端卡片视图
  const mobileCard = (item: TopListItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name}</div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="font-semibold">{item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}</div>
          {item.pct_change !== null && (
            <div className={item.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">交易日期:</span>
          <span>{item.trade_date || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜净买入:</span>
          {item.net_amount !== null && (
            <span className={item.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
              {item.net_amount >= 0 ? '+' : ''}{item.net_amount.toFixed(2)}万
            </span>
          )}
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜成交额:</span>
          <span>{item.l_amount !== null ? `${item.l_amount.toFixed(2)}万` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-gray-600">上榜理由:</span>
          <span className="text-xs break-all">{item.reason || '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="龙虎榜每日明细"
        description="龙虎榜每日交易明细数据，包含涨跌幅偏离值达7%、连续涨跌、换手率达20%等上榜股票及席位信息"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">上榜股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均净买入(万)</p>
                  <p className={`text-xl sm:text-2xl font-bold ${statistics.avg_net_amount >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.avg_net_amount >= 0 ? '+' : ''}{statistics.avg_net_amount.toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大净买入(万)</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    +{statistics.max_net_amount.toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均涨跌幅%</p>
                  <p className={`text-xl sm:text-2xl font-bold ${statistics.avg_pct_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.avg_pct_change >= 0 ? '+' : ''}{statistics.avg_pct_change.toFixed(2)}%
                  </p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                type="text"
                placeholder="如: 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={loadData} disabled={isLoading} className="flex-1 sm:flex-none">
                查询
              </Button>
              <Button onClick={handleSync} variant="outline" className="flex-1 sm:flex-none">
                同步数据
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            isLoading={isLoading}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>
    </div>
  )
}
