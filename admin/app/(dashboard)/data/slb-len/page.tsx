'use client'

import { useState, useEffect } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { slbLenApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import type { SlbLenData, SlbLenStatistics } from '@/lib/api/slb-len'

export default function SlbLenPage() {
  const [data, setData] = useState<SlbLenData[]>([])
  const [statistics, setStatistics] = useState<SlbLenStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  // 筛选条件
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll } = useTaskStore()

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true)

      const params = {
        start_date: startDate ? startDate.toISOString().split('T')[0] : undefined,
        end_date: endDate ? endDate.toISOString().split('T')[0] : undefined,
        limit: 30
      }

      const [dataRes, statsRes] = await Promise.all([
        slbLenApi.getSlbLen(params),
        slbLenApi.getSlbLenStatistics(params)
      ])

      if (dataRes.code === 200 && dataRes.data) {
        setData(dataRes.data.items || [])
      }

      if (statsRes.code === 200 && statsRes.data) {
        setStatistics(statsRes.data)
      }
    } catch (error) {
      console.error('加载转融资数据失败:', error)
      toast.error('加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 同步数据
  const handleSync = async () => {
    try {
      setIsSyncing(true)

      const params = {
        start_date: startDate ? startDate.toISOString().split('T')[0] : undefined,
        end_date: endDate ? endDate.toISOString().split('T')[0] : undefined
      }

      const response = await slbLenApi.syncSlbLenAsync(params)

      if (response.code === 200 && response.data) {
        // 添加到任务存储
        addTask({
          taskId: response.data.celery_task_id,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        // 立即触发轮询
        triggerPoll()

        toast.success('同步任务已提交，请在任务面板查看进度')

        // 延迟刷新数据
        setTimeout(() => {
          loadData().catch(() => {})
        }, 3000)
      } else {
        toast.error('提交同步任务失败')
      }
    } catch (error) {
      console.error('同步失败:', error)
      toast.error('同步失败')
    } finally {
      setIsSyncing(false)
    }
  }

  // 初始加载
  useEffect(() => {
    loadData()
  }, [])

  // 日期变化时重新加载
  useEffect(() => {
    if (startDate !== undefined || endDate !== undefined) {
      loadData()
    }
  }, [startDate, endDate])

  // 表格列定义
  const columns: Column<SlbLenData>[] = [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row: SlbLenData) => row.trade_date || '-'
    },
    {
      key: 'ob',
      header: '期初余额',
      accessor: (row: SlbLenData) => `${row.ob.toFixed(2)} 亿元`
    },
    {
      key: 'auc_amount',
      header: '竞价成交',
      accessor: (row: SlbLenData) => {
        const val = row.auc_amount
        return val === 0 ? '-' : `${val.toFixed(2)} 亿元`
      }
    },
    {
      key: 'repo_amount',
      header: '再借成交',
      accessor: (row: SlbLenData) => {
        const val = row.repo_amount
        return val === 0 ? '-' : `${val.toFixed(2)} 亿元`
      }
    },
    {
      key: 'repay_amount',
      header: '偿还金额',
      accessor: (row: SlbLenData) => {
        const val = row.repay_amount
        return val === 0 ? '-' : `${val.toFixed(2)} 亿元`
      }
    },
    {
      key: 'cb',
      header: '期末余额',
      accessor: (row: SlbLenData) => `${row.cb.toFixed(2)} 亿元`
    }
  ]

  // 格式化金额（亿元）
  const formatAmount = (amount: number | undefined | null) => {
    if (amount === null || amount === undefined) return '0.00'
    return amount.toFixed(2)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="转融资交易汇总"
        description="转融通融资汇总数据（期初余额、竞价成交、再借成交、偿还、期末余额）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均期末余额</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.avg_cb)} 亿元</div>
              <p className="text-xs text-muted-foreground mt-1">
                统计周期内平均值
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大期末余额</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.max_cb)} 亿元</div>
              <p className="text-xs text-muted-foreground mt-1">
                历史最高值
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">累计竞价成交</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.total_auc_amount)} 亿元</div>
              <p className="text-xs text-muted-foreground mt-1">
                统计周期累计值
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">累计偿还金额</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.total_repay_amount)} 亿元</div>
              <p className="text-xs text-muted-foreground mt-1">
                统计周期累计值
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex flex-col sm:flex-row gap-4 flex-1">
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-2 block">开始日期</label>
                <DatePicker
                  date={startDate}
                  onDateChange={setStartDate}
                  placeholder="选择开始日期"
                />
              </div>
              <div className="flex-1 min-w-[200px]">
                <label className="text-sm font-medium mb-2 block">结束日期</label>
                <DatePicker
                  date={endDate}
                  onDateChange={setEndDate}
                  placeholder="选择结束日期"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={loadData}
                disabled={isLoading}
                variant="outline"
              >
                {isLoading ? '加载中...' : '查询'}
              </Button>
              <Button
                onClick={handleSync}
                disabled={isSyncing}
              >
                {isSyncing ? '同步中...' : '同步数据'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>转融资数据列表</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage="暂无数据"
          />
        </CardContent>
      </Card>
    </div>
  )
}
