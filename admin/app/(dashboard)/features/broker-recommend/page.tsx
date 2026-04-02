'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { brokerRecommendApi, type BrokerRecommendData, type BrokerRecommendStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, Package, Calendar } from 'lucide-react'

export default function BrokerRecommendPage() {
  const [data, setData] = useState<BrokerRecommendData[]>([])
  const [statistics, setStatistics] = useState<BrokerRecommendStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // 筛选参数
  const [month, setMonth] = useState('')
  const [broker, setBroker] = useState('')
  const [tsCode, setTsCode] = useState('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(100)
  const [total, setTotal] = useState(0)

  // 同步对话框状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncMonth, setSyncMonth] = useState('')

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  const syncing = isTaskRunning('tasks.sync_broker_recommend')

  const loadData = useCallback(async (targetPage: number = 1) => {
    try {
      setIsLoading(true)

      const params: any = {
        page: targetPage,
        page_size: pageSize
      }
      if (month.trim()) params.month = month.trim()
      if (broker.trim()) params.broker = broker.trim()
      if (tsCode.trim()) params.ts_code = tsCode.trim()

      const response = await brokerRecommendApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message || '加载数据失败' })
    } finally {
      setIsLoading(false)
    }
  }, [month, broker, tsCode, pageSize])

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  // 组件卸载清理
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  const handleSyncConfirm = async () => {
    setShowSyncDialog(false)
    try {
      const params: any = {}
      if (syncMonth.trim()) params.month = syncMonth.trim()

      const response = await brokerRecommendApi.syncAsync(params)

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData(1).catch(() => {})
            toast.success('数据同步完成', { description: '券商荐股数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  const columns: Column<BrokerRecommendData>[] = [
    {
      key: 'month',
      header: '月度',
      width: 100,
      accessor: (row) => row.month
    },
    {
      key: 'broker',
      header: '券商名称',
      width: 130,
      accessor: (row) => row.broker
    },
    {
      key: 'ts_code',
      header: '股票代码',
      width: 110,
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-'
    }
  ]

  const mobileCard = (item: BrokerRecommendData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">月度</span>
        <span className="font-medium">{item.month}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">券商</span>
        <span className="font-medium">{item.broker}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票名称</span>
        <span className="font-medium">{item.name || '-'}</span>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="券商每月荐股"
        description="查看券商月度金股推荐数据，一般在每月1-3日内更新当月数据"
        details={<>
          <div>接口：broker_recommend</div>
          <a href="https://tushare.pro/document/2?doc_id=267" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setShowSyncDialog(true)} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 同步对话框 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步券商荐股数据</DialogTitle>
            <DialogDescription>
              选择同步月度（留空则同步当前月）。每月1-3日更新当月数据。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">月度（可选，格式 YYYY-MM）</label>
            <Input
              placeholder="如：2025-03，留空同步当前月"
              value={syncMonth}
              onChange={(e) => setSyncMonth(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSyncDialog(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">月度数</p>
                  <p className="text-2xl font-bold">{statistics.month_count}</p>
                  <p className="text-xs text-muted-foreground mt-1">已收录月度数</p>
                </div>
                <Calendar className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">券商数</p>
                  <p className="text-2xl font-bold">{statistics.broker_count}</p>
                  <p className="text-xs text-muted-foreground mt-1">参与推荐的券商</p>
                </div>
                <Building2 className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count}</p>
                  <p className="text-xs text-muted-foreground mt-1">被推荐的股票</p>
                </div>
                <TrendingUp className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_records}</p>
                  <p className="text-xs text-muted-foreground mt-1">所有推荐记录</p>
                </div>
                <Package className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据筛选</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="month">月度 (YYYY-MM)</Label>
              <Input
                id="month"
                placeholder="如: 2021-06"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="broker">券商名称</Label>
              <Input
                id="broker"
                placeholder="如: 东兴证券"
                value={broker}
                onChange={(e) => setBroker(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="ts_code">股票代码</Label>
              <Input
                id="ts_code"
                placeholder="如: 000066 或 000066.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => loadData(1)} disabled={isLoading} className="w-full">
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={data}
          loading={isLoading}
          emptyMessage="暂无数据"
          mobileCard={mobileCard}
          pagination={{
            page,
            pageSize,
            total,
            onPageChange: (newPage) => loadData(newPage),
            onPageSizeChange: () => loadData(1),
            pageSizeOptions: [50, 100, 200]
          }}
        />
      </Card>
    </div>
  )
}
