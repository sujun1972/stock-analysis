'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Activity, Building2, TrendingUp, TrendingDown } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import Link from 'next/link'

export default function DragonTigerListPage() {
  const searchParams = useSearchParams()
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(searchParams.get('date') || new Date().toISOString().split('T')[0])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const pageSize = 20

  const loadData = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getDragonTigerList({
        date,
        page,
        limit: pageSize
      })

      if (response.code === 200 && response.data) {
        setRecords(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        toast.error(response.message || '加载失败')
      }
    } catch (error: any) {
      console.error('加载龙虎榜失败:', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [date, page])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6 p-6">
      {/* 返回按钮 */}
      <Link href="/sentiment/data">
        <Button variant="ghost" size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回情绪总览
        </Button>
      </Link>

      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">龙虎榜</h1>
          <p className="text-muted-foreground mt-1">
            主力资金动向、机构席位明细
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

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              上榜股票
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{total}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              机构参与
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600">
              {records.filter(r => r.has_institution).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              净买入居多
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {records.filter(r => r.net_amount > 0).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 龙虎榜列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            龙虎榜明细
          </CardTitle>
          <CardDescription>
            共 {total} 只股票上榜
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">加载中...</div>
          ) : records.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {date} 没有龙虎榜数据
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {records.map((record) => (
                  <Card key={record.id} className="border-l-4" style={{
                    borderLeftColor: record.net_amount >= 0 ? '#22c55e' : '#ef4444'
                  }}>
                    <CardHeader className="pb-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            {record.stock_name}
                            <span className="font-mono text-sm text-muted-foreground">
                              {record.stock_code}
                            </span>
                            {record.has_institution && (
                              <Badge variant="secondary" className="ml-2">
                                <Building2 className="h-3 w-3 mr-1" />
                                机构{record.institution_count}家
                              </Badge>
                            )}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            {record.reason}
                          </CardDescription>
                        </div>
                        <div className="text-right">
                          <Badge variant={record.price_change >= 0 ? 'default' : 'destructive'}>
                            {record.price_change >= 0 ? '+' : ''}
                            {record.price_change.toFixed(2)}%
                          </Badge>
                          <div className="text-sm text-muted-foreground mt-1">
                            ¥{record.close_price.toFixed(2)}
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div className="text-center p-3 bg-green-50 rounded">
                          <div className="text-xs text-muted-foreground mb-1">买入总额</div>
                          <div className="text-lg font-bold text-green-600">
                            {(record.buy_amount / 10000).toFixed(0)}万
                          </div>
                        </div>
                        <div className="text-center p-3 bg-red-50 rounded">
                          <div className="text-xs text-muted-foreground mb-1">卖出总额</div>
                          <div className="text-lg font-bold text-red-600">
                            {(record.sell_amount / 10000).toFixed(0)}万
                          </div>
                        </div>
                        <div className="text-center p-3 bg-blue-50 rounded">
                          <div className="text-xs text-muted-foreground mb-1">净额</div>
                          <div className={`text-lg font-bold ${record.net_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {record.net_amount >= 0 ? '+' : ''}
                            {(record.net_amount / 10000).toFixed(0)}万
                          </div>
                        </div>
                      </div>

                      {/* 买卖席位 */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* 买入席位 */}
                        <div>
                          <div className="font-medium text-sm mb-2 flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-green-600" />
                            买入前五
                          </div>
                          <div className="space-y-1">
                            {record.top_buyers && record.top_buyers.length > 0 ? (
                              record.top_buyers.slice(0, 5).map((buyer: any, idx: number) => (
                                <div key={idx} className="text-sm p-2 bg-muted/50 rounded">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="truncate max-w-[200px] font-medium" title={buyer.name}>
                                      {buyer.rank}. {buyer.name}
                                    </span>
                                    {buyer.name.includes('机构') && (
                                      <Badge variant="secondary" className="text-xs ml-2">
                                        <Building2 className="h-3 w-3 mr-1" />
                                        机构
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>买: {(buyer.buy_amount / 10000).toFixed(0)}万</span>
                                    <span>卖: {(buyer.sell_amount / 10000).toFixed(0)}万</span>
                                    <span className={buyer.net_amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                                      净: {buyer.net_amount >= 0 ? '+' : ''}{(buyer.net_amount / 10000).toFixed(0)}万
                                    </span>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div className="text-xs text-muted-foreground text-center py-2">
                                暂无席位数据
                              </div>
                            )}
                          </div>
                        </div>

                        {/* 卖出席位 */}
                        <div>
                          <div className="font-medium text-sm mb-2 flex items-center gap-2">
                            <TrendingDown className="h-4 w-4 text-red-600" />
                            卖出前五
                          </div>
                          <div className="space-y-1">
                            {record.top_sellers && record.top_sellers.length > 0 ? (
                              record.top_sellers.slice(0, 5).map((seller: any, idx: number) => (
                                <div key={idx} className="text-sm p-2 bg-muted/50 rounded">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="truncate max-w-[200px] font-medium" title={seller.name}>
                                      {seller.rank}. {seller.name}
                                    </span>
                                    {seller.name.includes('机构') && (
                                      <Badge variant="secondary" className="text-xs ml-2">
                                        <Building2 className="h-3 w-3 mr-1" />
                                        机构
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>买: {(seller.buy_amount / 10000).toFixed(0)}万</span>
                                    <span>卖: {(seller.sell_amount / 10000).toFixed(0)}万</span>
                                    <span className={seller.net_amount >= 0 ? 'text-green-600' : 'text-red-600'}>
                                      净: {seller.net_amount >= 0 ? '+' : ''}{(seller.net_amount / 10000).toFixed(0)}万
                                    </span>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div className="text-xs text-muted-foreground text-center py-2">
                                暂无席位数据
                              </div>
                            )}
                          </div>
                        </div>
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
