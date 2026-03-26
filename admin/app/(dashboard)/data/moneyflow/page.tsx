'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MoneyflowData {
  trade_date: string
  ts_code: string
  buy_sm_vol: number
  buy_sm_amount: number
  sell_sm_vol: number
  sell_sm_amount: number
  buy_md_vol: number
  buy_md_amount: number
  sell_md_vol: number
  sell_md_amount: number
  buy_lg_vol: number
  buy_lg_amount: number
  sell_lg_vol: number
  sell_lg_amount: number
  buy_elg_vol: number
  buy_elg_amount: number
  sell_elg_vol: number
  sell_elg_amount: number
  net_mf_vol: number
  net_mf_amount: number
}

interface Statistics {
  avg_net: number
  max_net: number
  min_net: number
  total_net: number
  avg_elg: number
  max_elg: number
  avg_lg: number
  max_lg: number
  latest_date: string
  earliest_date: string
  count: number
  stock_count: number
}

export default function MoneyflowPage() {
  const [data, setData] = useState<MoneyflowData[]>([])
  const [topStocks, setTopStocks] = useState<MoneyflowData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选状态
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务回调引用
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      }

      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.getMoneyflow(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, tsCode, startDate, endDate])

  // 加载TOP排名
  const loadTopStocks = useCallback(async () => {
    try {
      const response = await apiClient.getTopMoneyflowTushare({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data.items || [])
      }
    } catch (err) {
      console.error('加载TOP排名失败:', err)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    loadData()
    loadTopStocks()
  }, [loadData, loadTopStocks])

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.syncMoneyflowAsync(params)

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
            loadTopStocks().catch(() => {})
            toast.success('数据同步完成', { description: '个股资金流向数据已更新' })
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
    } finally {
      setSyncing(false)
    }
  }

  // 组件卸载清理
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

  // 表格列定义
  const columns: Column<MoneyflowData>[] = useMemo(
    () => [
      {
        key: 'trade_date',
        header: '日期',
        width: 100,
        accessor: (row) => row.trade_date.slice(0, 4) + '-' + row.trade_date.slice(4, 6) + '-' + row.trade_date.slice(6, 8)
      },
      {
        key: 'ts_code',
        header: '代码',
        width: 100,
        accessor: (row) => row.ts_code
      },
      {
        key: 'net_mf_amount',
        header: '净流入额(万)',
        width: 120,
        accessor: (row) => {
          const value = row.net_mf_amount
          const color = value > 0 ? 'text-red-600' : value < 0 ? 'text-green-600' : 'text-gray-600'
          return <span className={color}>{value.toFixed(2)}</span>
        }
      },
      {
        key: 'buy_elg_amount',
        header: '特大单买(万)',
        width: 120,
        accessor: (row) => row.buy_elg_amount.toFixed(2)
      },
      {
        key: 'sell_elg_amount',
        header: '特大单卖(万)',
        width: 120,
        accessor: (row) => row.sell_elg_amount.toFixed(2)
      },
      {
        key: 'buy_lg_amount',
        header: '大单买(万)',
        width: 110,
        accessor: (row) => row.buy_lg_amount.toFixed(2)
      },
      {
        key: 'sell_lg_amount',
        header: '大单卖(万)',
        width: 110,
        accessor: (row) => row.sell_lg_amount.toFixed(2)
      },
      {
        key: 'buy_md_amount',
        header: '中单买(万)',
        width: 110,
        accessor: (row) => row.buy_md_amount.toFixed(2)
      },
      {
        key: 'sell_md_amount',
        header: '中单卖(万)',
        width: 110,
        accessor: (row) => row.sell_md_amount.toFixed(2)
      },
      {
        key: 'buy_sm_amount',
        header: '小单买(万)',
        width: 110,
        accessor: (row) => row.buy_sm_amount.toFixed(2)
      },
      {
        key: 'sell_sm_amount',
        header: '小单卖(万)',
        width: 110,
        accessor: (row) => row.sell_sm_amount.toFixed(2)
      }
    ],
    []
  )

  // 图表数据
  const chartData = useMemo(() => {
    return topStocks.map(item => ({
      code: item.ts_code,
      净流入额: parseFloat(item.net_mf_amount.toFixed(2)),
      特大单买: parseFloat(item.buy_elg_amount.toFixed(2)),
      大单买: parseFloat(item.buy_lg_amount.toFixed(2))
    }))
  }, [topStocks])

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <PageHeader
        title="个股资金流向（Tushare）"
        description="基于主动买卖单统计的资金流向数据（小单/中单/大单/特大单）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>平均净流入</CardDescription>
              <CardTitle className="text-2xl">{statistics.avg_net != null ? statistics.avg_net.toFixed(2) : '-'}万</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>累计净流入</CardDescription>
              <CardTitle className="text-2xl">{statistics.total_net != null ? statistics.total_net.toFixed(2) : '-'}万</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>最大净流入</CardDescription>
              <CardTitle className="text-2xl">{statistics.max_net != null ? statistics.max_net.toFixed(2) : '-'}万</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>统计股票数</CardDescription>
              <CardTitle className="text-2xl">{statistics.stock_count}只</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* TOP 20 图表 */}
      {topStocks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              净流入额TOP 20
            </CardTitle>
            <CardDescription>资金净流入排名（单位：万元）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="code"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="净流入额" fill="#8884d8" />
                    <Bar dataKey="特大单买" fill="#82ca9d" />
                    <Bar dataKey="大单买" fill="#ffc658" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和同步 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询与同步</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
              <div className="space-y-2">
                <Label>股票代码</Label>
                <Input
                  placeholder="如: 000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>开始日期</Label>
                <DatePicker
                  date={startDate}
                  onDateChange={setStartDate}
                  placeholder="选择开始日期"
                />
              </div>
              <div className="space-y-2">
                <Label>结束日期</Label>
                <DatePicker
                  date={endDate}
                  onDateChange={setEndDate}
                  placeholder="选择结束日期"
                />
              </div>
              <div className="flex gap-2">
                <Button variant="default" onClick={loadData} disabled={loading}>
                  查询
                </Button>
                <Button
                  variant="outline"
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
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>个股资金流向数据</CardTitle>
          <CardDescription className="flex flex-col sm:flex-row gap-2">
            <span>共 {total} 条记录 | 数据单位：万元</span>
            <span className="text-xs">小单&lt;5万 | 中单5-20万 | 大单20-100万 | 特大单≥100万</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无个股资金流向数据"
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
              }
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
