'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, TrendingUp, Activity, AlertCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import type { MarketSentiment } from '@/types/sentiment'
import { addTaskToQueue } from '@/hooks/use-task-polling'

export default function SentimentManagementPage() {
  const router = useRouter()
  const [sentiments, setSentiments] = useState<MarketSentiment[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const pageSize = 20

  // 获取北京时间
  const getBeijingTime = () => {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
  }

  // 获取今天的日期字符串（北京时间）
  const getTodayDate = () => {
    const beijingTime = getBeijingTime()
    const year = beijingTime.getFullYear()
    const month = String(beijingTime.getMonth() + 1).padStart(2, '0')
    const day = String(beijingTime.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}` // YYYY-MM-DD
  }

  // 判断当前市场状态和应该显示的数据
  const getMarketStatus = () => {
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
    // 收盘后统一判断：如果有今日数据显示，没有则隐藏
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
          shouldHideStats: !hasToday // 收盘后没有今日数据就隐藏
        }
      }

      // 17:30 之后（应该已经采集完成）
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
  }

  // 计算北京时间 17:30 对应的本地时间（用于页面提示）
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
  }, [sentiments]) // 当 sentiments 变化时重新计算

  // 当数据加载完成后，更新市场状态
  useEffect(() => {
    if (!loading && sentiments.length > 0) {
      setMarketStatus(getMarketStatus())
    }
  }, [loading, sentiments])

  // 加载数据
  const loadSentiments = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getSentimentList({
        page,
        limit: pageSize
      }) as any

      if (response.code === 200 && response.data) {
        setSentiments(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        toast.error(response.message || '加载失败')
      }
    } catch (error: any) {
      console.error('加载情绪数据失败:', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }

  // 手动同步（异步任务）
  const handleSync = async () => {
    setSyncing(true)
    try {
      const response = await apiClient.syncSentimentData() as any

      // 成功提交任务
      if (response.code === 200 && response.data) {
        const { task_id, date } = response.data

        // 显示任务提交成功的提示
        toast.info('同步任务已提交', {
          description: `正在同步 ${date} 的数据，请稍候...`,
          duration: 3000,
        })

        // 添加任务到全局轮询队列
        addTaskToQueue(task_id, '市场情绪数据同步')

        // 延迟刷新列表（给任务一些执行时间）
        setTimeout(() => {
          loadSentiments()
        }, 2000)
      }
      // 任务正在执行中（锁冲突）
      else if (response.code === 409) {
        toast.warning('同步任务正在执行中', {
          description: response.data?.reason || '已有同步任务正在进行，请等待其完成后再试',
          duration: 5000,
        })
      }
      // 其他错误
      else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (error: any) {
      console.error('提交同步任务失败:', error)
      toast.error('提交失败: ' + (error.message || '网络错误'))
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => {
    loadSentiments()
  }, [page])

  const totalPages = Math.ceil(total / pageSize)

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

      {/* 市场状态提示条 - 只在显示统计卡片时展示 */}
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
        /* 收盘后无数据时显示等待提示卡片 */
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
        /* 正常显示统计卡片 */
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

          <Card className="cursor-pointer hover:shadow-md transition-shadow border-orange-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">炸板率</CardTitle>
              <AlertCircle className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {sentiments[0]?.blast_rate ? (sentiments[0].blast_rate * 100).toFixed(1) + '%' : 'N/A'}
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
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
              <p>加载中...</p>
            </div>
          ) : sentiments.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <AlertCircle className="h-6 w-6 mx-auto mb-2" />
              <p>暂无数据</p>
              <Button onClick={handleSync} className="mt-4" variant="outline">
                立即同步数据
              </Button>
            </div>
          ) : (
            <>
              {/* 桌面端表格 */}
              <div className="hidden md:block overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead>上证指数</TableHead>
                      <TableHead>深成指数</TableHead>
                      <TableHead>创业板指</TableHead>
                      <TableHead>成交额(亿)</TableHead>
                      <TableHead>涨停</TableHead>
                      <TableHead>炸板率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sentiments.map((item) => (
                      <TableRow key={item.id} className="hover:bg-muted/50">
                        <TableCell className="font-medium">
                          {item.trade_date}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span>{item.sh_index_close?.toFixed(2) || '-'}</span>
                            {item.sh_index_change !== undefined && (
                              <Badge variant={item.sh_index_change >= 0 ? 'default' : 'destructive'} className="text-xs">
                                {item.sh_index_change >= 0 ? '+' : ''}
                                {item.sh_index_change.toFixed(2)}%
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span>{item.sz_index_close?.toFixed(2) || '-'}</span>
                            {item.sz_index_change !== undefined && (
                              <Badge variant={item.sz_index_change >= 0 ? 'default' : 'destructive'} className="text-xs">
                                {item.sz_index_change >= 0 ? '+' : ''}
                                {item.sz_index_change.toFixed(2)}%
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span>{item.cyb_index_close?.toFixed(2) || '-'}</span>
                            {item.cyb_index_change !== undefined && (
                              <Badge variant={item.cyb_index_change >= 0 ? 'default' : 'destructive'} className="text-xs">
                                {item.cyb_index_change >= 0 ? '+' : ''}
                                {item.cyb_index_change.toFixed(2)}%
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {item.total_amount ? (item.total_amount / 100000000).toFixed(0) : '-'}
                        </TableCell>
                        <TableCell>
                          <span className="text-green-600 font-medium">
                            {item.limit_up_count || 0}
                          </span>
                        </TableCell>
                        <TableCell>
                          {item.blast_rate !== undefined ? (
                            <Badge variant={item.blast_rate > 0.3 ? 'destructive' : 'secondary'}>
                              {(item.blast_rate * 100).toFixed(1)}%
                            </Badge>
                          ) : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* 移动端卡片 */}
              <div className="md:hidden space-y-4">
                {sentiments.map((item) => (
                  <Card key={item.id}>
                    <CardHeader>
                      <CardTitle className="text-lg">
                        {item.trade_date}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">上证指数</span>
                        <div className="flex items-center gap-2">
                          <span>{item.sh_index_close?.toFixed(2) || '-'}</span>
                          {item.sh_index_change !== undefined && (
                            <Badge variant={item.sh_index_change >= 0 ? 'default' : 'destructive'} className="text-xs">
                              {item.sh_index_change >= 0 ? '+' : ''}{item.sh_index_change.toFixed(2)}%
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">涨停家数</span>
                        <span className="text-green-600 font-medium">{item.limit_up_count || 0}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">炸板率</span>
                        {item.blast_rate !== undefined ? (
                          <Badge variant={item.blast_rate > 0.3 ? 'destructive' : 'secondary'}>
                            {(item.blast_rate * 100).toFixed(1)}%
                          </Badge>
                        ) : '-'}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    上一页
                  </Button>
                  <span className="px-4 py-2 text-sm">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage(page + 1)}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
