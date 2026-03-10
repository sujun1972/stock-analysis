'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, TrendingUp, TrendingDown, Activity, AlertCircle } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import { format } from 'date-fns'
import type { MarketSentiment } from '@/types/sentiment'

export default function SentimentManagementPage() {
  const [sentiments, setSentiments] = useState<MarketSentiment[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const pageSize = 20

  // 加载数据
  const loadSentiments = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getSentimentList({
        page,
        limit: pageSize
      })

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

  // 手动同步
  const handleSync = async () => {
    setSyncing(true)
    try {
      const response = await apiClient.syncSentimentData()
      if (response.code === 200) {
        toast.success('同步成功')
        await loadSentiments()
      } else {
        toast.error(response.message || '同步失败')
      }
    } catch (error: any) {
      console.error('同步失败:', error)
      toast.error('同步失败: ' + (error.message || '网络错误'))
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
            管理每日17:30采集的市场情绪指标数据
          </p>
        </div>
        <Button onClick={handleSync} disabled={syncing}>
          <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? '同步中...' : '手动同步'}
        </Button>
      </div>

      {/* 快捷入口卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow border-green-200"
              onClick={() => window.location.href = '/sentiment/limit-up'}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">涨停板池</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {sentiments[0]?.limit_up_count || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">今日涨停家数</p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow border-blue-200"
              onClick={() => window.location.href = '/sentiment/dragon-tiger'}>
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
            <p className="text-xs text-muted-foreground mt-1">市场情绪指标</p>
          </CardContent>
        </Card>
      </div>

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
