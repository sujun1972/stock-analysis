'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DataTable, Column } from '@/components/common/DataTable'
import { toast } from 'sonner'
import { RefreshCw } from 'lucide-react'
import { stockListApi } from '@/lib/api'
import type { StockListData, StockListStatistics } from '@/lib/api/stock-list-api'
import { useTaskStore } from '@/stores/task-store'
import { Database, TrendingUp, TrendingDown, PauseCircle, BarChart3 } from 'lucide-react'

export default function StockListPage() {
  const [data, setData] = useState<StockListData[]>([])
  const [statistics, setStatistics] = useState<StockListStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [listStatus, setListStatus] = useState<string>('all')
  const [market, setMarket] = useState<string>('all')
  const [exchange, setExchange] = useState<string>('all')
  const [isHs, setIsHs] = useState<string>('all')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const [syncDialogOpen, setSyncDialogOpen] = useState(false)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生——不要用本地 useState(false)
  const syncing = isTaskRunning('tasks.sync_stock_list')

  useEffect(() => {
    loadData().catch(() => {})
  }, [])

  // 分页变化时重新加载数据
  useEffect(() => {
    loadData().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize])

  // 组件卸载时清理所有活跃的任务回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadData = async () => {
    try {
      setIsLoading(true)

      const params: any = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      }

      if (listStatus !== 'all') {
        params.list_status = listStatus
      }

      if (market !== 'all') {
        params.market = market
      }

      if (exchange !== 'all') {
        params.exchange = exchange
      }

      if (isHs !== 'all') {
        params.is_hs = isHs
      }

      const [dataResponse, statsResponse] = await Promise.all([
        stockListApi.getData(params),
        stockListApi.getStatistics()
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total || dataResponse.data.items.length)
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error) {
      toast.error('加载数据失败')
      console.error(error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      // 不传任何查询筛选参数，让后端同步全部状态股票
      const response = await stockListApi.syncAsync()

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        if (!taskId) {
          toast.error('任务ID缺失')
          return
        }

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
            toast.success('数据同步完成', { description: '股票列表数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        triggerPoll()
        toast.success('同步任务已提交', { description: '同步全部股票数据（含上市/退市/停牌等状态）' })
      } else {
        toast.error(response.message || '同步任务提交失败')
      }
    } catch (error) {
      toast.error('同步任务提交失败')
      console.error(error)
    }
  }

  const columns: Column<StockListData>[] = [
    {
      key: 'code',
      header: '股票代码',
      accessor: (row) => row.code,
      className: 'font-mono'
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'ts_code',
      header: 'TS代码',
      accessor: (row) => row.ts_code || '-',
      className: 'font-mono hidden lg:table-cell'
    },
    {
      key: 'market',
      header: '市场',
      accessor: (row) => row.market,
      className: 'hidden md:table-cell'
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => row.exchange,
      className: 'hidden lg:table-cell'
    },
    {
      key: 'list_status',
      header: '上市状态',
      accessor: (row) => {
        const statusMap: { [key: string]: { text: string; color: string } } = {
          'L': { text: '上市', color: 'text-green-600' },
          'D': { text: '退市', color: 'text-red-600' },
          'P': { text: '暂停', color: 'text-yellow-600' },
          'G': { text: '过会', color: 'text-blue-600' }
        }
        const status = statusMap[row.list_status] || { text: row.list_status, color: '' }
        return <span className={status.color}>{status.text}</span>
      }
    },
    {
      key: 'is_hs',
      header: '沪深港通',
      accessor: (row) => (row.is_hs === 'S' || row.is_hs === 'H') ? '是' : '否',
      className: 'hidden md:table-cell'
    },
    {
      key: 'industry',
      header: '行业',
      accessor: (row) => row.industry || '-',
      className: 'hidden xl:table-cell'
    },
    {
      key: 'area',
      header: '地区',
      accessor: (row) => row.area || '-',
      className: 'hidden 2xl:table-cell'
    },
    {
      key: 'list_date',
      header: '上市日期',
      accessor: (row) => row.list_date || '-',
      className: 'hidden lg:table-cell'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票列表"
        description="获取基础信息数据，包括股票代码、名称、上市日期、退市日期等"
        details={<>
          <div>接口：stock_basic</div>
          <a href="https://tushare.pro/document/2?doc_id=25" target="_blank" rel="noopener noreferrer">查看文档</a>
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

      {/* 同步确认弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步股票列表</DialogTitle>
            <DialogDescription>
              将从 Tushare 同步全部股票数据（含上市、退市、停牌等状态），无需选择日期。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总股票数
              </CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                全部股票
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                上市股票
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{statistics.listed_count}</div>
              <p className="text-xs text-muted-foreground mt-1">正常交易</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                退市股票
              </CardTitle>
              <TrendingDown className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.delisted_count}</div>
              <p className="text-xs text-muted-foreground mt-1">已退市</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                停牌股票
              </CardTitle>
              <PauseCircle className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{statistics.suspended_count}</div>
              <p className="text-xs text-muted-foreground mt-1">暂停上市</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                沪深港通
              </CardTitle>
              <BarChart3 className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{statistics.hs_count}</div>
              <p className="text-xs text-muted-foreground mt-1">可通过港股通交易</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">上市状态</label>
              <Select value={listStatus} onValueChange={setListStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="L">上市</SelectItem>
                  <SelectItem value="D">退市</SelectItem>
                  <SelectItem value="P">暂停上市</SelectItem>
                  <SelectItem value="G">过会未交易</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">市场类型</label>
              <Select value={market} onValueChange={setMarket}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部市场</SelectItem>
                  <SelectItem value="主板">主板</SelectItem>
                  <SelectItem value="科创板">科创板</SelectItem>
                  <SelectItem value="创业板">创业板</SelectItem>
                  <SelectItem value="北交所">北交所</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">交易所</label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部交易所</SelectItem>
                  <SelectItem value="SSE">上海证券交易所</SelectItem>
                  <SelectItem value="SZSE">深圳证券交易所</SelectItem>
                  <SelectItem value="BSE">北京证券交易所</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">沪深港通</label>
              <Select value={isHs} onValueChange={setIsHs}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="S">沪股通</SelectItem>
                  <SelectItem value="H">深股通</SelectItem>
                  <SelectItem value="N">非港股通</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={loadData} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
            <Button
              onClick={() => {
                setListStatus('all')
                setMarket('all')
                setExchange('all')
                setIsHs('all')
              }}
              variant="ghost"
            >
              重置
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={(item) => (
              <div className="p-4 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono font-semibold">{item.code}</div>
                    <div className="text-sm text-muted-foreground">{item.name}</div>
                    {item.ts_code && (
                      <div className="text-xs text-muted-foreground font-mono">{item.ts_code}</div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${
                      item.list_status === 'L' ? 'text-green-600' :
                      item.list_status === 'D' ? 'text-red-600' :
                      item.list_status === 'P' ? 'text-yellow-600' :
                      'text-blue-600'
                    }`}>
                      {item.list_status === 'L' ? '上市' :
                       item.list_status === 'D' ? '退市' :
                       item.list_status === 'P' ? '暂停' :
                       '过会'}
                    </div>
                    {item.list_date && (
                      <div className="text-xs text-muted-foreground">{item.list_date}</div>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                  <div>
                    <div className="text-xs text-muted-foreground">市场</div>
                    <div className="text-sm font-medium">{item.market}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">交易所</div>
                    <div className="text-sm font-medium">{item.exchange}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">行业</div>
                    <div className="text-sm font-medium">{item.industry || '-'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">沪深港通</div>
                    <div className="text-sm font-medium">
                      {(item.is_hs === 'S' || item.is_hs === 'H') ? '是' : '否'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>
    </div>
  )
}
