'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DatePicker } from '@/components/ui/date-picker'
import { TrendingUp, AlertCircle, Zap } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import logger from '@/lib/logger'
import { format } from '@/lib/date-utils'
import { DataTable, Column } from '@/components/common/DataTable'

interface LimitUpStock {
  code: string
  name: string
  days: number
  reason?: string
  first_limit_time?: string
}

interface BlastStock {
  code: string
  name: string
  blast_times: number
  final_change?: number
}

export default function LimitUpPoolPage() {
  const searchParams = useSearchParams()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const dateParam = searchParams.get('date')
    return dateParam ? new Date(dateParam) : new Date()
  })

  // 涨停股票表格列配置
  const limitUpColumns: Column<LimitUpStock>[] = useMemo(() => [
    {
      key: 'code',
      header: '股票代码',
      cellClassName: 'font-mono'
    },
    {
      key: 'name',
      header: '股票名称',
      cellClassName: 'font-medium'
    },
    {
      key: 'days',
      header: '连板天数',
      render: (value: number) => (
        <Badge variant={value >= 3 ? 'destructive' : 'default'}>
          {value}连板
        </Badge>
      )
    },
    {
      key: 'reason',
      header: '涨停原因',
      cellClassName: 'text-sm text-muted-foreground max-w-xs truncate',
      render: (value: string | undefined) => value || '-'
    },
    {
      key: 'first_limit_time',
      header: '首次封板时间',
      cellClassName: 'text-sm',
      render: (value: string | undefined) => value || '-'
    }
  ], [])

  // 炸板股票表格列配置
  const blastColumns: Column<BlastStock>[] = useMemo(() => [
    {
      key: 'code',
      header: '股票代码',
      cellClassName: 'font-mono'
    },
    {
      key: 'name',
      header: '股票名称',
      cellClassName: 'font-medium'
    },
    {
      key: 'blast_times',
      header: '炸板次数',
      render: (value: number) => (
        <Badge variant="destructive">{value}次</Badge>
      )
    },
    {
      key: 'final_change',
      header: '最终涨跌幅',
      render: (value: number | undefined) => {
        const changeValue = value ?? 0
        return (
          <Badge variant={changeValue >= 0 ? 'default' : 'destructive'}>
            {changeValue >= 0 ? '+' : ''}
            {changeValue.toFixed(2)}%
          </Badge>
        )
      }
    }
  ], [])

  // 涨停股票移动端卡片渲染
  const limitUpMobileCard = useCallback((item: LimitUpStock) => (
    <div className="space-y-2">
      <div className="flex justify-between items-start">
        <div>
          <span className="font-mono text-sm">{item.code}</span>
          <p className="font-medium">{item.name}</p>
        </div>
        <Badge variant={item.days >= 3 ? 'destructive' : 'default'}>
          {item.days}连板
        </Badge>
      </div>
      {item.reason && (
        <p className="text-sm text-muted-foreground truncate">
          原因: {item.reason}
        </p>
      )}
      {item.first_limit_time && (
        <p className="text-xs text-muted-foreground">
          封板: {item.first_limit_time}
        </p>
      )}
    </div>
  ), [])

  // 炸板股票移动端卡片渲染
  const blastMobileCard = useCallback((item: BlastStock) => (
    <div className="space-y-2">
      <div className="flex justify-between items-start">
        <div>
          <span className="font-mono text-sm">{item.code}</span>
          <p className="font-medium">{item.name}</p>
        </div>
        <div className="flex flex-col gap-1 items-end">
          <Badge variant="destructive">{item.blast_times}次</Badge>
          <Badge variant={(item.final_change ?? 0) >= 0 ? 'default' : 'destructive'}>
            {(item.final_change ?? 0) >= 0 ? '+' : ''}
            {(item.final_change ?? 0).toFixed(2)}%
          </Badge>
        </div>
      </div>
    </div>
  ), [])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const dateStr = format(selectedDate, 'yyyy-MM-dd')
      const res = await apiClient.getLimitUpPool(dateStr) as any

      if (res.code === 200 && res.data) {
        setData(res.data)
      } else if (res.code === 404) {
        setData(null)
        toast.info(`${dateStr} 没有涨停板数据`)
      } else {
        toast.error(res.message || '加载失败')
      }
    } catch (error: any) {
      logger.error('加载涨停板数据失败', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }, [selectedDate])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 数据加载完成后，处理锚点滚动
  useEffect(() => {
    if (!loading && data) {
      // 延迟一小段时间确保DOM已渲染
      setTimeout(() => {
        const hash = window.location.hash
        if (hash) {
          const element = document.querySelector(hash)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }
      }, 100)
    }
  }, [loading, data])

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">涨停板池</h1>
          <p className="text-muted-foreground mt-1">
            涨停板、炸板率、连板天梯数据
          </p>
        </div>
        <div className="flex gap-2">
          <DatePicker
            date={selectedDate}
            onDateChange={(date) => {
              if (date) {
                setSelectedDate(date)
              }
            }}
            placeholder="选择日期"
            className="w-[240px]"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">加载中...</p>
        </div>
      ) : !data ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">暂无数据</p>
              <p className="text-sm text-muted-foreground mt-2">
                {format(selectedDate, 'yyyy-MM-dd')} 可能不是交易日或数据尚未采集
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 统计卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  涨停家数
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">
                  {data.limit_up_count}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  跌停家数
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">
                  {data.limit_down_count}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  炸板数量
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-orange-600">
                  {data.blast_count}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  炸板率
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${data.blast_rate > 0.3 ? 'text-red-600' : 'text-blue-600'}`}>
                  {(data.blast_rate * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 连板天梯 */}
          {data.continuous_ladder && Object.keys(data.continuous_ladder).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-yellow-500" />
                  连板天梯
                </CardTitle>
                <CardDescription>
                  最高{data.max_continuous_days}连板，共{data.max_continuous_count}只
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  {Object.entries(data.continuous_ladder)
                    .sort((a: any, b: any) => {
                      const aNum = parseInt(a[0])
                      const bNum = parseInt(b[0])
                      return bNum - aNum
                    })
                    .map(([days, count]: [string, any]) => (
                      <div key={days} className="text-center p-4 bg-muted rounded-lg">
                        <div className="text-2xl font-bold text-yellow-600">{count}</div>
                        <div className="text-sm text-muted-foreground mt-1">{days}</div>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 涨停股票列表 */}
          {data.limit_up_stocks && data.limit_up_stocks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  涨停股票明细
                </CardTitle>
                <CardDescription>
                  共 {data.limit_up_stocks.length} 只股票涨停
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  data={data.limit_up_stocks.slice(0, 50)}
                  columns={limitUpColumns}
                  mobileCard={limitUpMobileCard}
                  pageSize={20}
                  showPagination={data.limit_up_stocks.length > 20}
                />
                {data.limit_up_stocks.length > 50 && (
                  <p className="text-sm text-muted-foreground text-center mt-4">
                    仅显示前50只，共{data.limit_up_stocks.length}只
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* 炸板股票列表 */}
          {data.blast_stocks && data.blast_stocks.length > 0 && (
            <Card id="blast-stocks">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-orange-600" />
                  炸板股票明细
                </CardTitle>
                <CardDescription>
                  共 {data.blast_stocks.length} 只股票炸板
                </CardDescription>
              </CardHeader>
              <CardContent>
                <DataTable
                  data={data.blast_stocks.slice(0, 30)}
                  columns={blastColumns}
                  mobileCard={blastMobileCard}
                  pageSize={15}
                  showPagination={data.blast_stocks.length > 15}
                />
                {data.blast_stocks.length > 30 && (
                  <p className="text-sm text-muted-foreground text-center mt-4">
                    仅显示前30只，共{data.blast_stocks.length}只
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}