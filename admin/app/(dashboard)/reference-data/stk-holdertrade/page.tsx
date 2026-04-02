'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { stkHoldertradeApi, type StkHoldertradeData, type StkHoldertradeStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Users, FileText } from 'lucide-react'

export default function StkHoldertradePage() {
  const [data, setData] = useState<StkHoldertradeData[]>([])
  const [statistics, setStatistics] = useState<StkHoldertradeStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [holderType, setHolderType] = useState<string>('ALL')
  const [tradeType, setTradeType] = useState<string>('ALL')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(100)
  const [total, setTotal] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_stk_holdertrade')

  // 构建本地时间日期字符串
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode) params.ts_code = tsCode
      if (holderType && holderType !== 'ALL') params.holder_type = holderType
      if (tradeType && tradeType !== 'ALL') params.trade_type = tradeType

      const response = await stkHoldertradeApi.getStkHoldertrade(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.items?.length || 0)
        setStatistics(response.data.statistics || null)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message || '无法加载股东增减持数据' })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, holderType, tradeType, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await stkHoldertradeApi.syncAsync(params)

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
            loadData().catch(() => {})
            toast.success('数据同步完成', { description: '股东增减持数据已更新' })
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

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [])

  const formatHolderType = (type: string) => {
    const types: Record<string, string> = { 'G': '高管', 'P': '个人', 'C': '公司' }
    return types[type] || type
  }

  const formatTradeType = (type: string) => type === 'IN' ? '增持' : type === 'DE' ? '减持' : type

  const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
    if (num === null || num === undefined) return '-'
    return num.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  const columns: Column<StkHoldertradeData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'ann_date', header: '公告日期', accessor: (row) => row.ann_date },
    { key: 'holder_name', header: '股东名称', accessor: (row) => row.holder_name },
    { key: 'holder_type', header: '股东类型', accessor: (row) => formatHolderType(row.holder_type) },
    {
      key: 'in_de',
      header: '交易类型',
      accessor: (row) => (
        <span className={row.in_de === 'IN' ? 'text-red-600' : 'text-green-600'}>
          {formatTradeType(row.in_de)}
        </span>
      )
    },
    { key: 'change_vol', header: '变动数量', accessor: (row) => formatNumber(row.change_vol, 0) },
    { key: 'change_ratio', header: '占流通比例(%)', accessor: (row) => formatNumber(row.change_ratio, 2) },
    { key: 'avg_price', header: '平均价格', accessor: (row) => formatNumber(row.avg_price, 2) },
    { key: 'after_share', header: '变动后持股', accessor: (row) => formatNumber(row.after_share, 0) },
    { key: 'after_ratio', header: '变动后比例(%)', accessor: (row) => formatNumber(row.after_ratio, 2) }
  ], [])

  const mobileCard = useCallback((item: StkHoldertradeData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium">{item.ts_code}</span>
        <span className={`font-semibold ${item.in_de === 'IN' ? 'text-red-600' : 'text-green-600'}`}>
          {formatTradeType(item.in_de)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东名称</span>
        <span className="text-right">{item.holder_name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东类型</span>
        <span>{formatHolderType(item.holder_type)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">变动数量</span>
        <span>{formatNumber(item.change_vol, 0)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">占流通比例</span>
        <span>{formatNumber(item.change_ratio, 2)}%</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">平均价格</span>
        <span>{formatNumber(item.avg_price, 2)}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股东增减持"
        description="获取上市公司增减持数据，了解重要股东近期及历史上的股份增减变化"
        details={<>
          <div>接口：stk_holdertrade</div>
          <a href="https://tushare.pro/document/2?doc_id=175" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步数据</DialogTitle>
            <DialogDescription>选择同步日期范围（留空则同步最新数据）。</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最新数据" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最新数据" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">涉及 {statistics.stock_count} 只股票</p>
                </div>
                <FileText className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">增持记录</p>
                  <p className="text-2xl font-bold text-red-600">{statistics.increase_count?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">平均比例 {formatNumber(statistics.avg_increase_ratio, 2)}%</p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">减持记录</p>
                  <p className="text-2xl font-bold text-green-600">{statistics.decrease_count?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">平均比例 {formatNumber(statistics.avg_decrease_ratio, 2)}%</p>
                </div>
                <TrendingDown className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">累计变动</p>
                  <div className="text-sm mt-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-red-600">增持:</span>
                      <span className="font-semibold">{formatNumber(statistics.total_increase_vol, 0)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-600">减持:</span>
                      <span className="font-semibold">{formatNumber(statistics.total_decrease_vol, 0)}</span>
                    </div>
                  </div>
                </div>
                <Users className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input placeholder="输入股票代码" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股东类型</label>
              <Select value={holderType} onValueChange={setHolderType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="G">高管</SelectItem>
                  <SelectItem value="P">个人</SelectItem>
                  <SelectItem value="C">公司</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">交易类型</label>
              <Select value={tradeType} onValueChange={setTradeType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="IN">增持</SelectItem>
                  <SelectItem value="DE">减持</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button onClick={loadData} disabled={loading}>查询</Button>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无股东增减持数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
              onPageSizeChange: () => {},
              pageSizeOptions: [100]
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
