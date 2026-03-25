'use client'

import { useState, useEffect, useCallback } from 'react'
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
import { cyqPerfApi, type CyqPerfData } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { Download, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'

export default function CyqPerfPage() {
  const [data, setData] = useState<CyqPerfData[]>([])
  const [allData, setAllData] = useState<CyqPerfData[]>([])
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

      const response = await cyqPerfApi.getData(params)

      if (response.code === 200 && response.data) {
        const items = response.data.items || []
        setAllData(items)
        setTotal(items.length)
        setCurrentPage(1)  // 重置到第一页
        setStatistics(response.data.statistics || null)
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

    try {
      const params = {
        ts_code: syncTsCode,
        start_date: syncStartDate ? syncStartDate.toISOString().split('T')[0] : undefined,
        end_date: syncEndDate ? syncEndDate.toISOString().split('T')[0] : undefined
      }

      const response = await cyqPerfApi.syncAsync(params)

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

  const columns: Column<CyqPerfData>[] = [
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
      header: '历史最低价',
      accessor: (row) => row.his_low?.toFixed(2) || '-',
      key: 'his_low'
    },
    {
      header: '历史最高价',
      accessor: (row) => row.his_high?.toFixed(2) || '-',
      key: 'his_high'
    },
    {
      header: '5%成本',
      accessor: (row) => row.cost_5pct?.toFixed(2) || '-',
      key: 'cost_5pct'
    },
    {
      header: '15%成本',
      accessor: (row) => row.cost_15pct?.toFixed(2) || '-',
      key: 'cost_15pct'
    },
    {
      header: '50%成本',
      accessor: (row) => row.cost_50pct?.toFixed(2) || '-',
      key: 'cost_50pct',
      className: 'font-semibold'
    },
    {
      header: '85%成本',
      accessor: (row) => row.cost_85pct?.toFixed(2) || '-',
      key: 'cost_85pct'
    },
    {
      header: '95%成本',
      accessor: (row) => row.cost_95pct?.toFixed(2) || '-',
      key: 'cost_95pct'
    },
    {
      header: '加权平均成本',
      accessor: (row) => row.weight_avg?.toFixed(2) || '-',
      key: 'weight_avg',
      className: 'font-semibold'
    },
    {
      header: '胜率(%)',
      accessor: (row) => {
        const rate = row.winner_rate
        if (rate === null || rate === undefined) return '-'
        const className = rate >= 60 ? 'text-red-600' : rate <= 40 ? 'text-green-600' : ''
        return (
          <span className={className}>
            {rate.toFixed(2)}%
          </span>
        )
      },
      key: 'winner_rate',
      sortable: true,
      className: 'font-semibold'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日筹码及胜率"
        description="A股每日筹码平均成本和胜率情况，数据从2018年开始，每天18-19点更新"
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
              <CardTitle className="text-sm font-medium">平均胜率</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.avg_winner_rate?.toFixed(2) || 0}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.date_range || ''}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最高胜率</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {statistics.max_winner_rate?.toFixed(2) || 0}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.max_date || ''}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最低胜率</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statistics.min_winner_rate?.toFixed(2) || 0}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {statistics.min_date || ''}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均成本</CardTitle>
              <Download className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ¥{statistics.avg_weight_avg?.toFixed(2) || 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                加权平均成本
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
            输入股票代码查询筹码及胜率数据
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
                onDateChange={setQueryStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={queryEndDate}
                onDateChange={setQueryEndDate}
                placeholder="选择结束日期"
              />
            </div>

            <Button onClick={loadData} disabled={isLoading || !queryTsCode}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>筹码及胜率数据</CardTitle>
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
            pageSizeOptions={[10, 20, 50, 100]}
          />
        </CardContent>
      </Card>

      {/* 同步数据对话框 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步筹码及胜率数据</DialogTitle>
            <DialogDescription>
              从Tushare接口同步每日筹码及胜率数据（5000积分/次）
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
                onDateChange={setSyncStartDate}
                placeholder="选择开始日期"
              />
              <p className="text-xs text-muted-foreground">
                可选，不填则从数据起始日期（2018年）开始
              </p>
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={syncEndDate}
                onDateChange={setSyncEndDate}
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
