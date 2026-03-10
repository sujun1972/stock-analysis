'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ArrowLeft, TrendingUp, AlertCircle, Zap } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import Link from 'next/link'

export default function LimitUpPoolPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getLimitUpPool(date)

      if (response.code === 200 && response.data) {
        setData(response.data)
      } else if (response.code === 404) {
        setData(null)
        toast.info(`${date} 没有涨停板数据`)
      } else {
        toast.error(response.message || '加载失败')
      }
    } catch (error: any) {
      console.error('加载涨停板数据失败:', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [date])

  return (
    <div className="space-y-6 p-6">
      {/* 返回按钮 */}
      <Link href="/sentiment">
        <Button variant="ghost" size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回情绪总览
        </Button>
      </Link>

      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">涨停板池</h1>
          <p className="text-muted-foreground mt-1">
            涨停板、炸板率、连板天梯数据
          </p>
        </div>
        <div className="flex gap-2">
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-40"
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
                {date} 可能不是交易日或数据尚未采集
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>股票代码</TableHead>
                      <TableHead>股票名称</TableHead>
                      <TableHead>连板天数</TableHead>
                      <TableHead>涨停原因</TableHead>
                      <TableHead>首次封板时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.limit_up_stocks.slice(0, 50).map((stock: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono">{stock.code}</TableCell>
                        <TableCell className="font-medium">{stock.name}</TableCell>
                        <TableCell>
                          <Badge variant={stock.days >= 3 ? 'destructive' : 'default'}>
                            {stock.days}连板
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                          {stock.reason || '-'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {stock.first_limit_time || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
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
            <Card>
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>股票代码</TableHead>
                      <TableHead>股票名称</TableHead>
                      <TableHead>炸板次数</TableHead>
                      <TableHead>最终涨跌幅</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.blast_stocks.slice(0, 30).map((stock: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono">{stock.code}</TableCell>
                        <TableCell className="font-medium">{stock.name}</TableCell>
                        <TableCell>
                          <Badge variant="destructive">{stock.blast_times}次</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={stock.final_change >= 0 ? 'default' : 'destructive'}>
                            {stock.final_change >= 0 ? '+' : ''}
                            {stock.final_change?.toFixed(2) || 0}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
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
