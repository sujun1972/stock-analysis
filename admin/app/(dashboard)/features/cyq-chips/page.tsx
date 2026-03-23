'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { cyqChipsApi, type CyqChipsData } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { BarChart3, TrendingUp, TrendingDown, Download } from 'lucide-react'

export default function CyqChipsPage() {
  const [data, setData] = useState<CyqChipsData[]>([])
  const [allData, setAllData] = useState<CyqChipsData[]>([])
  const [statistics, setStatistics] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)

  // 查询条件
  const [queryTsCode, setQueryTsCode] = useState('')
  const [queryStartDate, setQueryStartDate] = useState<Date | undefined>(undefined)
  const [queryEndDate, setQueryEndDate] = useState<Date | undefined>(undefined)

  // 同步对话框
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll } = useTaskStore()
  const taskCompletedRef = useRef(false)

  // 更新分页数据
  const updatePaginatedData = useCallback(() => {
    const startIndex = (currentPage - 1) * pageSize
    const endIndex = startIndex + pageSize
    setData(allData.slice(startIndex, endIndex))
  }, [allData, currentPage, pageSize])

  useEffect(() => {
    updatePaginatedData()
  }, [updatePaginatedData])

  const loadData = useCallback(async () => {
    if (!queryTsCode) {
      toast.error('请输入股票代码')
      return
    }

    setIsLoading(true)
    try {
      const params = {
        ts_code: queryTsCode,
        start_date: queryStartDate ? queryStartDate.toISOString().split('T')[0] : undefined,
        end_date: queryEndDate ? queryEndDate.toISOString().split('T')[0] : undefined,
        limit: 1000  // 增加限制，一次获取更多数据用于分页
      }

      const response = await cyqChipsApi.getData(params)

      if (response.code === 200 && response.data) {
        const items = response.data.items || []
        setAllData(items)
        setTotal(items.length)
        setCurrentPage(1)  // 重置到第一页

        // 获取统计数据
        const statsParams = {
          ts_code: queryTsCode,
          start_date: queryStartDate ? queryStartDate.toISOString().split('T')[0] : undefined,
          end_date: queryEndDate ? queryEndDate.toISOString().split('T')[0] : undefined,
        }
        const statsResponse = await cyqChipsApi.getStatistics(statsParams)
        if (statsResponse.code === 200 && statsResponse.data) {
          setStatistics(statsResponse.data)
        }

        toast.success(`成功加载 ${items.length} 条数据`)
      } else {
        toast.error(response.message || '加载数据失败')
      }
    } catch (error: any) {
      console.error('加载数据失败:', error)
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }, [queryTsCode, queryStartDate, queryEndDate])

  const handleOpenSyncDialog = () => {
    // 打开对话框时，如果查询条件有值，自动填充到同步参数
    if (queryTsCode) {
      setSyncTsCode(queryTsCode)
    }
    if (queryStartDate) {
      setSyncStartDate(queryStartDate)
    }
    if (queryEndDate) {
      setSyncEndDate(queryEndDate)
    }
    setShowSyncDialog(true)
  }

  const handleSync = async () => {
    if (!syncTsCode) {
      toast.error('请输入股票代码')
      return
    }

    setIsSyncing(true)
    taskCompletedRef.current = false

    try {
      const params = {
        ts_code: syncTsCode,
        start_date: syncStartDate ? syncStartDate.toISOString().split('T')[0] : undefined,
        end_date: syncEndDate ? syncEndDate.toISOString().split('T')[0] : undefined
      }

      const response = await cyqChipsApi.syncAsync(params)

      if (response.code === 200 && response.data) {
        addTask({
          taskId: response.data.celery_task_id,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
          onComplete: () => {
            if (!taskCompletedRef.current) {
              taskCompletedRef.current = true
              toast.success('数据同步完成，正在加载数据...')

              // 同步完成后，自动设置查询条件并刷新数据
              setTimeout(() => {
                // 如果查询条件与同步条件不同，更新查询条件
                if (queryTsCode !== syncTsCode) {
                  setQueryTsCode(syncTsCode)
                  setQueryStartDate(syncStartDate)
                  setQueryEndDate(syncEndDate)
                }

                // 使用同步的参数重新加载数据
                const params = {
                  ts_code: syncTsCode,
                  start_date: syncStartDate ? syncStartDate.toISOString().split('T')[0] : undefined,
                  end_date: syncEndDate ? syncEndDate.toISOString().split('T')[0] : undefined,
                  limit: 1000
                }

                setIsLoading(true)
                cyqChipsApi.getData(params)
                  .then(response => {
                    if (response.code === 200 && response.data) {
                      const items = response.data.items || []
                      setAllData(items)
                      setTotal(items.length)
                      setCurrentPage(1)

                      // 加载统计数据
                      const statsParams = {
                        ts_code: syncTsCode,
                        start_date: syncStartDate ? syncStartDate.toISOString().split('T')[0] : undefined,
                        end_date: syncEndDate ? syncEndDate.toISOString().split('T')[0] : undefined,
                      }
                      cyqChipsApi.getStatistics(statsParams)
                        .then(statsResp => {
                          if (statsResp.code === 200 && statsResp.data) {
                            setStatistics(statsResp.data)
                          }
                        })
                        .catch(err => console.error('加载统计数据失败:', err))

                      toast.success(`成功加载 ${items.length} 条数据`)
                    }
                  })
                  .catch(error => {
                    console.error('加载数据失败:', error)
                    toast.error('加载数据失败')
                  })
                  .finally(() => {
                    setIsLoading(false)
                  })
              }, 2000)
            }
          },
          onError: (error) => {
            toast.error(`同步失败: ${error}`)
          }
        })

        triggerPoll()
        setShowSyncDialog(false)
        toast.success(response.message || '同步任务已提交')
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (error: any) {
      console.error('同步失败:', error)
      toast.error(error.message || '同步失败')
    } finally {
      setIsSyncing(false)
    }
  }

  useEffect(() => {
    return () => {
      taskCompletedRef.current = false
    }
  }, [])

  // 移动端卡片视图
  const renderMobileCard = (item: CyqChipsData) => (
    <div key={`${item.ts_code}-${item.trade_date}`} className="bg-white p-4 border-b divide-y hover:bg-blue-50 active:bg-blue-100 transition-colors">
      <div className="flex justify-between py-2">
        <span className="text-xs font-medium text-muted-foreground">股票代码</span>
        <span className="text-sm font-semibold">{item.ts_code}</span>
      </div>
      <div className="flex justify-between py-2">
        <span className="text-xs font-medium text-muted-foreground">交易日期</span>
        <span className="text-sm">
          {item.trade_date && item.trade_date.length === 8
            ? `${item.trade_date.slice(0, 4)}-${item.trade_date.slice(4, 6)}-${item.trade_date.slice(6, 8)}`
            : item.trade_date}
        </span>
      </div>
      <div className="flex justify-between py-2">
        <span className="text-xs font-medium text-muted-foreground">价格</span>
        <span className="text-sm">{item.price !== null ? item.price.toFixed(2) : '-'}</span>
      </div>
      <div className="flex justify-between py-2">
        <span className="text-xs font-medium text-muted-foreground">占比(%)</span>
        <span className="text-sm">{item.percent !== null ? item.percent.toFixed(2) : '-'}</span>
      </div>
    </div>
  )

  const columns: Column<CyqChipsData>[] = [
    {
      header: '股票代码',
      accessor: (row) => row.ts_code,
      key: 'ts_code',
      sortable: true
    },
    {
      header: '交易日期',
      accessor: (row) => {
        const date = row.trade_date
        if (!date || date.length !== 8) return date
        return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
      },
      key: 'trade_date',
      sortable: true
    },
    {
      header: '价格',
      accessor: (row) => row.price !== null ? row.price.toFixed(2) : '-',
      key: 'price'
    },
    {
      header: '占比(%)',
      accessor: (row) => row.percent !== null ? row.percent.toFixed(2) : '-',
      key: 'percent',
      className: 'font-semibold'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日筹码分布"
        description="A股每日筹码分布数据，包含各价格区间的筹码占比，数据每天18-19点更新"
        actions={
          <Button onClick={handleOpenSyncDialog}>
            同步数据
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.total_records || 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                筹码分布数据条数
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数</CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {statistics.stock_count || 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                覆盖股票数量
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">日期数</CardTitle>
              <TrendingDown className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">
                {statistics.date_count || 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                覆盖交易日期数
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均价格</CardTitle>
              <Download className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ¥{statistics.avg_price !== null ? statistics.avg_price.toFixed(2) : '0.00'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.min_price !== null && statistics.max_price !== null
                  ? `${statistics.min_price.toFixed(2)} - ${statistics.max_price.toFixed(2)}`
                  : ''}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>
            输入股票代码查询筹码分布数据
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
            <div className="space-y-2">
              <Label htmlFor="ts_code">股票代码 *</Label>
              <Input
                id="ts_code"
                placeholder="例如: 000001.SZ"
                value={queryTsCode}
                onChange={(e) => setQueryTsCode(e.target.value.toUpperCase())}
              />
            </div>

            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={queryStartDate}
                onSelect={setQueryStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={queryEndDate}
                onSelect={setQueryEndDate}
                placeholder="选择结束日期"
              />
            </div>

            <Button onClick={loadData} disabled={isLoading || !queryTsCode}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格（桌面端） */}
      <Card className="hidden sm:block">
        <CardHeader>
          <CardTitle>筹码分布数据</CardTitle>
          <CardDescription>
            共 {total} 条记录，当前显示第 {total > 0 ? (currentPage - 1) * pageSize + 1 : 0} - {Math.min(currentPage * pageSize, total)} 条
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage={queryTsCode ? '暂无数据' : '请输入股票代码并点击查询'}
            page={currentPage}
            pageSize={pageSize}
            total={total}
            onPageChange={setCurrentPage}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize)
              setCurrentPage(1)  // 切换每页数量时重置到第一页
            }}
            pageSizeOptions={[10, 20, 50, 100, 500, 1000]}
          />
        </CardContent>
      </Card>

      {/* 数据卡片（移动端） */}
      <Card className="sm:hidden">
        <CardHeader>
          <CardTitle>筹码分布数据</CardTitle>
          <CardDescription>
            共 {total} 条记录，当前显示第 {total > 0 ? (currentPage - 1) * pageSize + 1 : 0} - {Math.min(currentPage * pageSize, total)} 条
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          ) : data.length > 0 ? (
            <>
              <div className="space-y-0">
                {data.map((item, index) => (
                  <div
                    key={`${item.ts_code}-${item.trade_date}-${index}`}
                    className={`${
                      index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                    } p-4 border-b last:border-b-0 hover:bg-blue-50 active:bg-blue-100 transition-colors`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-semibold text-base">{item.ts_code}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.trade_date && item.trade_date.length === 8
                          ? `${item.trade_date.slice(0, 4)}-${item.trade_date.slice(4, 6)}-${item.trade_date.slice(6, 8)}`
                          : item.trade_date}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">价格</span>
                        <span className="font-medium">
                          {item.price !== null ? `¥${item.price.toFixed(2)}` : '-'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">占比</span>
                        <span className="font-medium">
                          {item.percent !== null ? `${item.percent.toFixed(2)}%` : '-'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 移动端分页控制 */}
              <div className="mt-6 space-y-3">
                <div className="flex justify-between items-center text-sm text-muted-foreground">
                  <span>第 {total > 0 ? currentPage : 0} / {Math.ceil(total / pageSize)} 页</span>
                  <span>{pageSize} 条/页</span>
                </div>
                <div className="flex gap-2 justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage <= 1}
                  >
                    上一页
                  </Button>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value))
                      setCurrentPage(1)
                    }}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    <option value="10">10</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                  </select>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.min(Math.ceil(total / pageSize), currentPage + 1))}
                    disabled={currentPage >= Math.ceil(total / pageSize)}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex justify-center items-center h-32">
              <p className="text-muted-foreground">
                {queryTsCode ? '暂无数据' : '请输入股票代码并点击查询'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 同步数据对话框 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步筹码分布数据</DialogTitle>
            <DialogDescription>
              从Tushare接口同步每日筹码分布数据（5000积分/次）
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="sync_ts_code">股票代码 *</Label>
              <Input
                id="sync_ts_code"
                placeholder="例如: 000001.SZ"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value.toUpperCase())}
              />
              <p className="text-xs text-muted-foreground">
                必填项，指定要同步的股票代码
              </p>
            </div>

            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={syncStartDate}
                onSelect={setSyncStartDate}
                placeholder="选择开始日期"
              />
              <p className="text-xs text-muted-foreground">
                可选，不填则从数据起始日期开始
              </p>
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={syncEndDate}
                onSelect={setSyncEndDate}
                placeholder="选择结束日期"
              />
              <p className="text-xs text-muted-foreground">
                可选，不填则同步到最新日期
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowSyncDialog(false)}
              disabled={isSyncing}
            >
              取消
            </Button>
            <Button onClick={handleSync} disabled={isSyncing || !syncTsCode}>
              {isSyncing ? '同步中...' : '开始同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
