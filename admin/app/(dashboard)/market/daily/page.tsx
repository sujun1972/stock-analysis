'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDataPage } from '@/hooks/useDataPage'
import { stockDailyApi } from '@/lib/api'
import type { StockDailyData, StockDailyStatistics, FullHistoryProgressData } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, Database, Calendar, BarChart3, History } from 'lucide-react'

export default function StockDailyPage() {
  // 查询筛选状态
  const [code, setCode] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // 同步参数（独立于查询筛选）
  const [syncCode, setSyncCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState('')
  const [syncEndDate, setSyncEndDate] = useState('')
  const [syncYears, setSyncYears] = useState(5)

  // 独立统计 + 全量历史进度（useDataPage 不管理这些）
  const [localStats, setLocalStats] = useState<StockDailyStatistics | null>(null)
  const [fullHistoryProgress, setFullHistoryProgress] = useState<FullHistoryProgressData | null>(null)

  const { isTaskRunning, addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const fullHistorySyncing = isTaskRunning('tasks.sync_daily_full_history')
  const activeCallbacksRef = useRef<Map<string, (task: any) => void>>(new Map())

  const dp = useDataPage<StockDailyData>({
    apiCall: (params) => stockDailyApi.getData(params),
    taskName: 'tasks.sync_daily_single',
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (code) params.code = code
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate
      return params
    },
  })

  // 加载独立统计信息
  useEffect(() => {
    stockDailyApi.getStatistics().then((resp) => {
      if (resp.code === 200) setLocalStats(resp.data || null)
    }).catch(() => {})
  }, [])

  // 加载全量同步进度
  const loadFullHistoryProgress = useCallback(async () => {
    try {
      const resp = await stockDailyApi.getFullHistoryProgress()
      if (resp.code === 200 && resp.data) setFullHistoryProgress(resp.data)
    } catch { /* silent */ }
  }, [])

  useEffect(() => { loadFullHistoryProgress() }, [loadFullHistoryProgress])

  // 清理回调
  useEffect(() => {
    const callbacks = activeCallbacksRef.current
    return () => {
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSync = async () => {
    try {
      const params = {
        code: syncCode || undefined,
        start_date: syncStartDate || undefined,
        end_date: syncEndDate || undefined,
        years: syncYears,
      }
      const response = await stockDailyApi.syncAsync(params)
      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id
        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            dp.loadData(1)
            stockDailyApi.getStatistics().then((r) => { if (r.code === 200) setLocalStats(r.data || null) }).catch(() => {})
            toast.success('数据同步完成', { description: '日线数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()
        toast.success('任务已提交', { description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度` })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '无法同步数据'
      toast.error('同步失败', { description: message })
    }
  }

  const handleFullHistorySync = async () => {
    try {
      const response = await stockDailyApi.syncFullHistory()
      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id
        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            dp.loadData(1)
            loadFullHistoryProgress()
            toast.success('全量历史同步完成')
          } else if (task.status === 'failure') {
            toast.error('全量历史同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()
        toast.success('全量同步任务已提交', { description: '将逐只同步全部上市股票自2021年起的日线数据，中断后可续继' })
      } else {
        throw new Error(response.message || '提交失败')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '无法提交全量同步任务'
      toast.error('提交失败', { description: message })
    }
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!localStats) return []
    return [
      { label: '股票数量', value: localStats.stock_count.toLocaleString(), subValue: '上市股票总数', icon: BarChart3, iconColor: 'text-blue-600' },
      { label: '记录总数', value: localStats.record_count.toLocaleString(), subValue: '日线数据条数（近似值）', icon: Database, iconColor: 'text-orange-600' },
      { label: '最新交易日', value: localStats.latest_date || '-', subValue: `数据起始 ${localStats.earliest_date}`, icon: Calendar, iconColor: 'text-green-600' },
    ]
  }, [localStats])

  // 表格列定义
  const columns: Column<StockDailyData>[] = useMemo(() => [
    { key: 'code', header: '代码', accessor: (row) => row.code },
    { key: 'name', header: '名称', accessor: (row) => row.name },
    { key: 'date', header: '日期', accessor: (row) => typeof row.date === 'string' ? row.date.split('T')[0] : row.date },
    { key: 'close', header: '收盘价', accessor: (row) => row.close?.toFixed(2) || '-' },
    {
      key: 'pct_change',
      header: '涨跌幅',
      accessor: (row) => (
        <span className={
          (row.pct_change ?? 0) > 0 ? 'text-red-600 font-medium' :
          (row.pct_change ?? 0) < 0 ? 'text-green-600 font-medium' :
          'text-gray-600'
        }>
          {row.pct_change !== null && row.pct_change !== undefined
            ? `${row.pct_change > 0 ? '+' : ''}${row.pct_change.toFixed(2)}%`
            : '-'}
        </span>
      ),
    },
    { key: 'open', header: '开盘', accessor: (row) => row.open?.toFixed(2) || '-' },
    { key: 'high', header: '最高', accessor: (row) => row.high?.toFixed(2) || '-' },
    { key: 'low', header: '最低', accessor: (row) => row.low?.toFixed(2) || '-' },
    { key: 'volume', header: '成交量', accessor: (row) => row.volume !== null ? (row.volume / 10000).toFixed(2) + '万手' : '-' },
    { key: 'amount', header: '成交额', accessor: (row) => row.amount !== null ? (row.amount / 100000000).toFixed(2) + '亿' : '-' },
    { key: 'amplitude', header: '振幅', accessor: (row) => row.amplitude !== null ? row.amplitude.toFixed(2) + '%' : '-' },
    { key: 'turnover', header: '换手率', accessor: (row) => row.turnover !== null ? row.turnover.toFixed(2) + '%' : '-' },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StockDailyData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票</span>
        <span className="font-medium">{item.code} {item.name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">日期</span>
        <span>{item.date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span className="font-medium">{item.close?.toFixed(2) || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">涨跌幅</span>
        <span className={`font-medium ${
          (item.pct_change ?? 0) > 0 ? 'text-red-600' :
          (item.pct_change ?? 0) < 0 ? 'text-green-600' :
          'text-gray-600'
        }`}>
          {item.pct_change !== null && item.pct_change !== undefined
            ? `${item.pct_change > 0 ? '+' : ''}${item.pct_change.toFixed(2)}%`
            : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交额</span>
        <span>{item.amount !== null ? (item.amount / 100000000).toFixed(2) + '亿' : '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="A股日线行情"
        description="交易日每天15点～16点之间入库。本接口是未复权行情，停牌期间不提供数据"
        details={<>
          <div>接口：daily</div>
          <a href="https://tushare.pro/document/2?doc_id=27" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={handleSync} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <Button onClick={handleFullHistorySync} disabled={fullHistorySyncing} variant="outline">
              {fullHistorySyncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />全量同步中...</>
              ) : (
                <><History className="h-4 w-4 mr-1" />全量同步</>
              )}
            </Button>
          </div>
        }
      />

      <StatisticsCards items={statsCards} className="grid grid-cols-1 sm:grid-cols-3 gap-4" />

      {/* 全量历史同步进度 */}
      {fullHistoryProgress && (fullHistoryProgress.is_in_progress || fullHistoryProgress.completed > 0) && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">历史全量同步进度</CardTitle>
            <History className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                已完成 <span className="font-medium text-gray-900 dark:text-gray-100">{fullHistoryProgress.completed.toLocaleString()}</span> /
                共 <span className="font-medium text-gray-900 dark:text-gray-100">{fullHistoryProgress.total.toLocaleString()}</span> 只股票
              </span>
              <span className="text-sm font-bold">{fullHistoryProgress.percent}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${fullHistoryProgress.percent}%` }}
              />
            </div>
            {!fullHistoryProgress.is_in_progress && fullHistoryProgress.completed > 0 && fullHistoryProgress.completed < fullHistoryProgress.total && (
              <p className="text-xs text-amber-600 mt-2">
                任务已中断，点击「历史全量同步」可从断点续继（自动跳过已同步的 {fullHistoryProgress.completed.toLocaleString()} 只股票）
              </p>
            )}
            {fullHistoryProgress.is_in_progress && (
              <p className="text-xs text-blue-600 mt-2">同步任务正在进行中...</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* 数据查询 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码</label>
                <Input placeholder="如：000001" value={code} onChange={(e) => setCode(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${dp.isLoading ? 'animate-spin' : ''}`} />
                查询
              </Button>
              <Button onClick={() => { setCode(''); setStartDate(''); setEndDate('') }} variant="outline">
                重置
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据同步 */}
      <Card>
        <CardHeader>
          <CardTitle>数据同步</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码（可选）</label>
                <Input placeholder="如：000001.SZ（留空则同步全市场）" value={syncCode} onChange={(e) => setSyncCode(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <Input type="date" value={syncStartDate} onChange={(e) => setSyncStartDate(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <Input type="date" value={syncEndDate} onChange={(e) => setSyncEndDate(e.target.value)} />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">或者年数</label>
                <Input type="number" min={1} max={20} value={syncYears} onChange={(e) => setSyncYears(Number(e.target.value))} />
              </div>
            </div>
            <div className="text-sm text-gray-500">
              提示：留空股票代码将同步全市场数据（使用最近交易日）。指定股票代码可同步该股票的历史数据（默认{syncYears}年）
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={dp.data}
          loading={dp.isLoading}
          emptyMessage="暂无日线数据"
          mobileCard={mobileCard}
          pagination={{
            page: dp.page,
            pageSize: dp.pageSize,
            total: dp.total,
            onPageChange: dp.handlePageChange,
          }}
        />
      </Card>
    </div>
  )
}
