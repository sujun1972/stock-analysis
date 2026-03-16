/**
 * 市场情绪数据管理页面
 *
 * 功能：
 * - 显示每日市场情绪指标数据
 * - 支持手动同步数据
 * - 展示市场状态和统计信息
 * - 提供快捷入口到其他分析页面
 *
 * 使用 DataTable 组件自动处理表格展示和响应式布局
 */
'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, type Column } from '@/components/common/DataTable'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, TrendingUp, Activity, AlertCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import type { MarketSentiment } from '@/types/sentiment'
import { addTaskToQueue } from '@/hooks/use-task-polling'
import logger from '@/lib/logger'

export default function SentimentManagementPage() {
  const router = useRouter()
  const [sentiments, setSentiments] = useState<MarketSentiment[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const pageSize = 20

  // 安全地格式化数字
  const safeFormatNumber = (value: any, decimals: number = 2): string => {
    if (value === null || value === undefined || value === '') return '-'
    const num = typeof value === 'number' ? value : parseFloat(value)
    return isNaN(num) ? '-' : num.toFixed(decimals)
  }

  // 获取北京时间
  const getBeijingTime = () => {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
  }

  // 获取今天的日期字符串（北京时间）
  const getTodayDate = useCallback(() => {
    const beijingTime = getBeijingTime()
    const year = beijingTime.getFullYear()
    const month = String(beijingTime.getMonth() + 1).padStart(2, '0')
    const day = String(beijingTime.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}` // YYYY-MM-DD
  }, [])

  // 判断当前市场状态和应该显示的数据
  const getMarketStatus = useCallback(() => {
    const beijingTime = getBeijingTime()
    const hour = beijingTime.getHours()
    const minute = beijingTime.getMinutes()
    const day = beijingTime.getDay() // 0=周日, 1-5=周一至周五, 6=周六
    const timeInMinutes = hour * 60 + minute
    const today = getTodayDate()
    const latestDataDate = sentiments[0]?.trade_date

    // 周末
    if (day === 0 || day === 6) {
      return {
        status: 'weekend',
        label: '最新',
        description: '非交易日，显示最近交易日数据',
        showDate: true,
        shouldHideStats: false
      }
    }

    // 工作日：盘中时段 (09:30 - 15:00)
    if (timeInMinutes >= 9 * 60 + 30 && timeInMinutes < 15 * 60) {
      return {
        status: 'trading',
        label: '昨日',
        description: '盘中时段，显示昨日数据',
        showDate: false,
        shouldHideStats: false
      }
    }

    // 工作日：收盘后 (15:00 之后)
    if (timeInMinutes >= 15 * 60) {
      const hasToday = latestDataDate === today

      // 15:00-17:30 等待数据采集
      if (timeInMinutes < 17 * 60 + 30) {
        return {
          status: 'waiting_collection',
          label: hasToday ? '今日' : '等待采集',
          description: hasToday
            ? '今日数据（已采集）'
            : `等待 17:30 自动采集数据，或点击"手动同步"立即获取`,
          showDate: !hasToday,
          shouldHideStats: !hasToday
        }
      }

      // 17:30 之后
      return {
        status: 'after_market',
        label: hasToday ? '今日' : '数据未就绪',
        description: hasToday
          ? '盘后数据（已采集）'
          : '17:30 自动采集可能失败，请手动同步数据',
        showDate: !hasToday,
        shouldHideStats: !hasToday
      }
    }

    // 工作日：盘前时段 (00:00 - 09:30)
    return {
      status: 'pre_market',
      label: '昨日',
      description: '盘前时段，显示昨日数据',
      showDate: false,
      shouldHideStats: false
    }
  }, [sentiments, getTodayDate])

  // 计算北京时间 17:30 对应的本地时间
  const getLocalTimeFromBeijing = () => {
    const today = new Date()
    const beijingTime = new Date(today.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
    beijingTime.setHours(17, 30, 0, 0)

    const localOffset = new Date().getTimezoneOffset()
    const beijingOffset = -480 // 北京时间是 UTC+8 = -480 分钟
    const offsetDiff = beijingOffset - localOffset

    const localTime = new Date(beijingTime.getTime() + offsetDiff * 60 * 1000)

    return localTime.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  // 实时更新市场状态
  const [marketStatus, setMarketStatus] = useState(getMarketStatus())

  useEffect(() => {
    // 每分钟更新一次市场状态
    const timer = setInterval(() => {
      setMarketStatus(getMarketStatus())
    }, 60000) // 60秒

    return () => clearInterval(timer)
  }, [sentiments, getMarketStatus])

  // 当数据加载完成后，更新市场状态
  useEffect(() => {
    if (!loading && sentiments.length > 0) {
      setMarketStatus(getMarketStatus())
    }
  }, [loading, sentiments, getMarketStatus])

  // 加载数据
  const loadSentiments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiClient.getSentimentList({
        page,
        limit: pageSize
      }) as any

      if (res.code === 200 && res.data) {
        setSentiments(res.data.items || [])
        setTotal(res.data.total || 0)
      } else {
        toast.error(res.message || '加载失败')
      }
    } catch (error: any) {
      logger.error('加载情绪数据失败', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }, [page])

  // 手动同步
  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await apiClient.syncSentimentData() as any

      if (res.code === 200 && res.data) {
        const { task_id, date } = res.data

        toast.info('同步任务已提交', {
          description: `正在同步 ${date} 的数据，请稍候...`,
          duration: 3000,
        })

        addTaskToQueue(task_id, '市场情绪数据同步')

        setTimeout(() => {
          loadSentiments()
        }, 2000)
      }
      else if (res.code === 409) {
        toast.warning('同步任务正在执行中', {
          description: res.data?.reason || '已有同步任务正在进行，请等待其完成后再试',
          duration: 5000,
        })
      }
      else {
        toast.error(res.message || '提交同步任务失败')
      }
    } catch (error: any) {
      logger.error('提交同步任务失败', error)
      toast.error('提交失败: ' + (error.message || '网络错误'))
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    loadSentiments()
  }, [loadSentiments])

  // 定义表格列
  const columns: Column<MarketSentiment>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      cellClassName: 'font-medium',
    },
    {
      key: 'sh_index',
      header: '上证指数',
      accessor: (item) => (
        <div className="flex items-center gap-2">
          <span>{safeFormatNumber(item.sh_index_close)}</span>
          {item.sh_index_change !== undefined && item.sh_index_change !== null && !isNaN(Number(item.sh_index_change)) && (
            <Badge variant={Number(item.sh_index_change) >= 0 ? 'default' : 'destructive'} className="text-xs">
              {Number(item.sh_index_change) >= 0 ? '+' : ''}
              {safeFormatNumber(item.sh_index_change)}%
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'sz_index',
      header: '深成指数',
      accessor: (item) => (
        <div className="flex items-center gap-2">
          <span>{safeFormatNumber(item.sz_index_close)}</span>
          {item.sz_index_change !== undefined && item.sz_index_change !== null && !isNaN(Number(item.sz_index_change)) && (
            <Badge variant={Number(item.sz_index_change) >= 0 ? 'default' : 'destructive'} className="text-xs">
              {Number(item.sz_index_change) >= 0 ? '+' : ''}
              {safeFormatNumber(item.sz_index_change)}%
            </Badge>
          )}
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'cyb_index',
      header: '创业板指',
      accessor: (item) => (
        <div className="flex items-center gap-2">
          <span>{safeFormatNumber(item.cyb_index_close)}</span>
          {item.cyb_index_change !== undefined && item.cyb_index_change !== null && !isNaN(Number(item.cyb_index_change)) && (
            <Badge variant={Number(item.cyb_index_change) >= 0 ? 'default' : 'destructive'} className="text-xs">
              {Number(item.cyb_index_change) >= 0 ? '+' : ''}
              {safeFormatNumber(item.cyb_index_change)}%
            </Badge>
          )}
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'total_amount',
      header: '成交额(亿)',
      accessor: (item) => safeFormatNumber(item.total_amount ? item.total_amount / 100000000 : null, 0),
      align: 'right',
    },
    {
      key: 'limit_up_count',
      header: '涨停',
      accessor: (item) => (
        <Link href={`/sentiment/limit-up?date=${item.trade_date}`}>
          <span className="text-green-600 font-medium cursor-pointer hover:underline">
            {item.limit_up_count || 0}
          </span>
        </Link>
      ),
      align: 'center',
    },
    {
      key: 'blast_rate',
      header: '炸板率',
      accessor: (item) => (
        <Link href={`/sentiment/limit-up?date=${item.trade_date}#blast-stocks`}>
          {item.blast_rate !== undefined && item.blast_rate !== null && !isNaN(Number(item.blast_rate)) ? (
            <Badge variant={Number(item.blast_rate) > 0.3 ? 'destructive' : 'secondary'} className="cursor-pointer hover:opacity-80">
              {safeFormatNumber(Number(item.blast_rate) * 100, 1)}%
            </Badge>
          ) : '-'}
        </Link>
      ),
      align: 'center',
    },
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((item: MarketSentiment) => (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {item.trade_date}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">上证指数</span>
          <div className="flex items-center gap-2">
            <span>{safeFormatNumber(item.sh_index_close)}</span>
            {item.sh_index_change !== undefined && item.sh_index_change !== null && !isNaN(Number(item.sh_index_change)) && (
              <Badge variant={Number(item.sh_index_change) >= 0 ? 'default' : 'destructive'} className="text-xs">
                {Number(item.sh_index_change) >= 0 ? '+' : ''}{safeFormatNumber(item.sh_index_change)}%
              </Badge>
            )}
          </div>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">成交额</span>
          <span>{safeFormatNumber(item.total_amount ? item.total_amount / 100000000 : null, 0)}亿</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">涨停家数</span>
          <Link href={`/sentiment/limit-up?date=${item.trade_date}`}>
            <span className="text-green-600 font-medium">{item.limit_up_count || 0}</span>
          </Link>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">炸板率</span>
          <Link href={`/sentiment/limit-up?date=${item.trade_date}#blast-stocks`}>
            {item.blast_rate !== undefined && item.blast_rate !== null && !isNaN(Number(item.blast_rate)) ? (
              <Badge variant={Number(item.blast_rate) > 0.3 ? 'destructive' : 'secondary'}>
                {safeFormatNumber(Number(item.blast_rate) * 100, 1)}%
              </Badge>
            ) : '-'}
          </Link>
        </div>
        <div className="flex gap-2 pt-2">
          <Link href={`/sentiment/dragon-tiger?date=${item.trade_date}`} className="w-full">
            <Button variant="outline" size="sm" className="w-full">
              查看龙虎榜
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  ), [])

  // 操作列
  const actions = useCallback((item: MarketSentiment) => (
    <Link href={`/sentiment/dragon-tiger?date=${item.trade_date}`}>
      <Button variant="outline" size="sm">
        龙虎榜
      </Button>
    </Link>
  ), [])

  return (
    <div className="space-y-6 p-6">
      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">市场情绪管理</h1>
          <p className="text-muted-foreground mt-1">
            管理每日 <span className="font-medium text-foreground">17:30</span> (北京时间 UTC+8，本地时间 <span className="font-medium text-foreground">{getLocalTimeFromBeijing()}</span>) 采集的市场情绪指标数据
          </p>
        </div>
        <Button onClick={handleSync} disabled={syncing}>
          <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? '同步中...' : '手动同步'}
        </Button>
      </div>

      {/* 市场状态提示条 */}
      {marketStatus && !marketStatus.shouldHideStats && (
        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm ${
          marketStatus.status === 'trading' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
          marketStatus.status === 'waiting_collection' ? 'bg-orange-50 text-orange-700 border border-orange-200' :
          marketStatus.status === 'after_market' ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-gray-50 text-gray-700 border border-gray-200'
        }`}>
          <Activity className="h-4 w-4" />
          <span>{marketStatus.description}</span>
        </div>
      )}

      {/* 快捷入口卡片 */}
      {marketStatus.shouldHideStats ? (
        <Card className={`${
          marketStatus.status === 'waiting_collection'
            ? 'border-orange-200 bg-orange-50/50'
            : 'border-yellow-200 bg-yellow-50/50'
        }`}>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <AlertCircle className={`h-12 w-12 mb-4 ${
                marketStatus.status === 'waiting_collection' ? 'text-orange-600' : 'text-yellow-600'
              }`} />
              <h3 className={`text-lg font-semibold mb-2 ${
                marketStatus.status === 'waiting_collection' ? 'text-orange-900' : 'text-yellow-900'
              }`}>
                {marketStatus.status === 'waiting_collection' ? '等待数据采集' : '等待今日数据'}
              </h3>
              <p className={`text-sm mb-6 max-w-md ${
                marketStatus.status === 'waiting_collection' ? 'text-orange-700' : 'text-yellow-700'
              }`}>
                {marketStatus.status === 'waiting_collection'
                  ? '市场已收盘（15:00），系统将在 17:30 自动采集今日数据。您也可以点击下方按钮立即手动同步。'
                  : '已过自动采集时间（17:30），但今日数据尚未同步。可能是自动采集失败，请手动同步数据。'}
              </p>
              <div className="flex gap-3">
                <Button onClick={handleSync} disabled={syncing} size="lg">
                  <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                  {syncing ? '同步中...' : marketStatus.status === 'waiting_collection' ? '立即同步' : '手动同步'}
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => loadSentiments()}
                  disabled={loading}
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  刷新页面
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="cursor-pointer hover:shadow-md transition-shadow border-purple-200"
                onClick={() => router.push('/sentiment/cycle')}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">情绪周期</CardTitle>
              <Activity className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">周期分析</div>
              <p className="text-xs text-muted-foreground mt-1">赚钱效应与资金动向</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-md transition-shadow border-green-200"
                onClick={() => router.push('/sentiment/limit-up')}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">涨停板池</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {sentiments[0]?.limit_up_count || 0}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {marketStatus.label}涨停家数
                {marketStatus.showDate && sentiments[0]?.trade_date && (
                  <span className="ml-1">({sentiments[0].trade_date})</span>
                )}
              </p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-md transition-shadow border-blue-200"
                onClick={() => router.push('/sentiment/dragon-tiger')}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">龙虎榜</CardTitle>
              <Activity className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">查看详情</div>
              <p className="text-xs text-muted-foreground mt-1">主力资金动向</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:shadow-md transition-shadow border-orange-200"
                onClick={() => sentiments[0]?.trade_date && router.push(`/sentiment/limit-up?date=${sentiments[0].trade_date}#blast-stocks`)}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">炸板率</CardTitle>
              <AlertCircle className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {sentiments[0]?.blast_rate !== undefined && sentiments[0]?.blast_rate !== null && !isNaN(Number(sentiments[0]?.blast_rate))
                  ? safeFormatNumber(Number(sentiments[0].blast_rate) * 100, 1) + '%'
                  : 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {marketStatus.label}市场情绪
                {marketStatus.showDate && sentiments[0]?.trade_date && (
                  <span className="ml-1">({sentiments[0].trade_date})</span>
                )}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>历史数据</CardTitle>
          <CardDescription>共 {total} 条记录</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={sentiments}
            columns={columns}
            loading={loading}
            emptyMessage={
              <div className="text-center py-12 text-muted-foreground">
                <AlertCircle className="h-6 w-6 mx-auto mb-2" />
                <p>暂无数据</p>
                <Button onClick={handleSync} className="mt-4" variant="outline">
                  立即同步数据
                </Button>
              </div>
            }
            loadingMessage="加载中..."
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
            }}
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(item) => item.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}