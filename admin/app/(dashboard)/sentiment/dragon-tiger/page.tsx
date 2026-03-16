'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DatePicker } from '@/components/ui/date-picker'
import { Activity, Building2, TrendingUp, TrendingDown } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import logger from '@/lib/logger'
import { format } from '@/lib/date-utils'

/**
 * 龙虎榜席位信息
 */
interface Seat {
  rank: number
  name: string
  buy_amount: number | string
  sell_amount: number | string
  net_amount: number | string
}

/**
 * 龙虎榜记录
 */
interface DragonTigerRecord {
  id: number
  stock_code: string
  stock_name: string
  reason: string
  price_change: number | string
  close_price: number | string
  buy_amount: number | string
  sell_amount: number | string
  net_amount: number | string
  has_institution: boolean
  institution_count: number
  top_buyers?: Seat[]
  top_sellers?: Seat[]
}

/**
 * 工具函数：安全地转换为数字
 */
const toNumber = (value: number | string): number => {
  return typeof value === 'number' ? value : Number(value)
}

/**
 * 工具函数：格式化金额（转换为万元）
 */
const formatAmount = (amount: number | string): string => {
  return (toNumber(amount) / 10000).toFixed(0)
}

export default function DragonTigerListPage() {
  const searchParams = useSearchParams()
  const [records, setRecords] = useState<DragonTigerRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const dateParam = searchParams.get('date')
    return dateParam ? new Date(dateParam) : new Date()
  })
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const pageSize = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const dateStr = format(selectedDate, 'yyyy-MM-dd')
      const res = await apiClient.getDragonTigerList({
        date: dateStr,
        page,
        limit: pageSize
      }) as any

      if (res.code === 200 && res.data) {
        setRecords(res.data.items || [])
        setTotal(res.data.total || 0)
      } else {
        toast.error(res.message || '加载失败')
      }
    } catch (error: any) {
      logger.error('加载龙虎榜失败', error)
      toast.error('加载失败: ' + (error.message || '网络错误'))
    } finally {
      setLoading(false)
    }
  }, [selectedDate, page])

  useEffect(() => {
    loadData()
  }, [loadData])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">龙虎榜</h1>
          <p className="text-muted-foreground mt-1">
            主力资金动向、机构席位明细
          </p>
        </div>
        <div className="flex gap-2">
          <DatePicker
            date={selectedDate}
            onDateChange={(date) => {
              if (date) {
                setSelectedDate(date)
                setPage(1) // 重置页码
              }
            }}
            placeholder="选择日期"
            className="w-[240px]"
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
              {records.filter(r => toNumber(r.net_amount) > 0).length}
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
              {format(selectedDate, 'yyyy-MM-dd')} 没有龙虎榜数据
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {records.map((record) => {
                  const priceChange = toNumber(record.price_change)
                  const netAmount = toNumber(record.net_amount)

                  return (
                    <Card key={record.id} className="border-l-4" style={{
                      borderLeftColor: netAmount >= 0 ? '#22c55e' : '#ef4444'
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
                            <Badge variant={priceChange >= 0 ? 'default' : 'destructive'}>
                              {priceChange >= 0 ? '+' : ''}
                              {priceChange.toFixed(2)}%
                            </Badge>
                            <div className="text-sm text-muted-foreground mt-1">
                              ¥{toNumber(record.close_price).toFixed(2)}
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                          <div className="text-center p-3 bg-green-50 rounded">
                            <div className="text-xs text-muted-foreground mb-1">买入总额</div>
                            <div className="text-lg font-bold text-green-600">
                              {formatAmount(record.buy_amount)}万
                            </div>
                          </div>
                          <div className="text-center p-3 bg-red-50 rounded">
                            <div className="text-xs text-muted-foreground mb-1">卖出总额</div>
                            <div className="text-lg font-bold text-red-600">
                              {formatAmount(record.sell_amount)}万
                            </div>
                          </div>
                          <div className="text-center p-3 bg-blue-50 rounded">
                            <div className="text-xs text-muted-foreground mb-1">净额</div>
                            <div className={`text-lg font-bold ${netAmount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {netAmount >= 0 ? '+' : ''}
                              {formatAmount(record.net_amount)}万
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
                              record.top_buyers.slice(0, 5).map((buyer, idx) => {
                                const buyerNetAmount = toNumber(buyer.net_amount)
                                return (
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
                                      <span>买: {formatAmount(buyer.buy_amount)}万</span>
                                      <span>卖: {formatAmount(buyer.sell_amount)}万</span>
                                      <span className={buyerNetAmount >= 0 ? 'text-green-600' : 'text-red-600'}>
                                        净: {buyerNetAmount >= 0 ? '+' : ''}{formatAmount(buyer.net_amount)}万
                                      </span>
                                    </div>
                                  </div>
                                )
                              })
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
                              record.top_sellers.slice(0, 5).map((seller, idx) => {
                                const sellerNetAmount = toNumber(seller.net_amount)
                                return (
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
                                      <span>买: {formatAmount(seller.buy_amount)}万</span>
                                      <span>卖: {formatAmount(seller.sell_amount)}万</span>
                                      <span className={sellerNetAmount >= 0 ? 'text-green-600' : 'text-red-600'}>
                                        净: {sellerNetAmount >= 0 ? '+' : ''}{formatAmount(seller.net_amount)}万
                                      </span>
                                    </div>
                                  </div>
                                )
                              })
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
                  )
                })}
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
