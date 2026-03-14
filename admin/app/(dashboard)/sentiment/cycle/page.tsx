'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { RefreshCw, TrendingUp, TrendingDown, Activity, Users, Building2, AlertCircle } from 'lucide-react'
import type {
  SentimentCycle,
  InstitutionTopStock,
  HotMoneyLimitUpStock,
  HotMoneySeat
} from '@/types/sentiment'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SentimentCyclePage() {
  const [loading, setLoading] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)
  const [currentCycle, setCurrentCycle] = useState<SentimentCycle | null>(null)
  const [institutionTop, setInstitutionTop] = useState<InstitutionTopStock[]>([])
  const [hotMoneyTop, setHotMoneyTop] = useState<HotMoneyLimitUpStock[]>([])
  const [hotMoneyRanking, setHotMoneyRanking] = useState<HotMoneySeat[]>([])

  // 获取当前情绪周期
  const fetchCurrentCycle = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sentiment/cycle/current`)
      const data = await res.json()
      if (data.code === 200 && data.data) {
        setCurrentCycle(data.data)
        setError(null)
      } else if (data.code === 404) {
        setError('暂无情绪周期数据，请先采集数据并计算')
      }
    } catch (error) {
      console.error('获取当前情绪周期失败:', error)
      setError('获取情绪周期数据失败')
    }
  }

  // 获取机构排行
  const fetchInstitutionTop = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sentiment/hot-money/institution-top?limit=3`)
      const data = await res.json()
      if (data.code === 200) {
        setInstitutionTop(data.data || [])
      }
    } catch (error) {
      console.error('获取机构排行失败:', error)
    }
  }

  // 获取游资打板排行
  const fetchHotMoneyTop = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sentiment/hot-money/top-tier-limit-up?limit=10`)
      const data = await res.json()
      if (data.code === 200) {
        setHotMoneyTop(data.data || [])
      }
    } catch (error) {
      console.error('获取游资打板排行失败:', error)
    }
  }

  // 获取游资活跃度排行
  const fetchHotMoneyRanking = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sentiment/hot-money/activity-ranking?days=30&limit=20`)
      const data = await res.json()
      if (data.code === 200) {
        setHotMoneyRanking(data.data || [])
      }
    } catch (error) {
      console.error('获取游资活跃度排行失败:', error)
    }
  }

  // 计算情绪周期
  const calculateCycle = async () => {
    setCalculating(true)
    setError(null)
    setInfoMessage(null)
    try {
      const today = new Date().toISOString().split('T')[0]
      const res = await fetch(`${API_BASE}/api/sentiment/cycle/calculate?date=${today}`, {
        method: 'POST'
      })
      const data = await res.json()

      if (data.code === 200) {
        // 显示成功消息（如果日期被自动调整，会包含说明）
        if (data.message && data.message !== '计算成功') {
          // 使用信息提示显示调整信息
          setInfoMessage(data.message)
          setTimeout(() => setInfoMessage(null), 6000)
        } else {
          setInfoMessage('计算成功')
          setTimeout(() => setInfoMessage(null), 3000)
        }
        // 计算成功后刷新数据
        await refreshAll()
      } else {
        setError(data.message || '计算失败')
      }
    } catch (error) {
      console.error('计算情绪周期失败:', error)
      setError('计算失败，请稍后重试')
    } finally {
      setCalculating(false)
    }
  }

  // 刷新所有数据
  const refreshAll = async () => {
    setLoading(true)
    try {
      await Promise.all([
        fetchCurrentCycle(),
        fetchInstitutionTop(),
        fetchHotMoneyTop(),
        fetchHotMoneyRanking()
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshAll()
  }, [])

  // 获取阶段颜色
  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      '冰点': 'bg-blue-500 text-white',
      '启动': 'bg-green-500 text-white',
      '发酵': 'bg-red-500 text-white',
      '退潮': 'bg-yellow-500 text-white'
    }
    return colors[stage] || 'bg-gray-500 text-white'
  }

  // 格式化金额
  const formatAmount = (amount: number) => {
    if (amount >= 100000000) {
      return `${(amount / 100000000).toFixed(2)}亿`
    } else if (amount >= 10000) {
      return `${(amount / 10000).toFixed(0)}万`
    } else {
      return amount.toFixed(0)
    }
  }

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">市场情绪周期分析</h1>
          <p className="text-muted-foreground mt-1">实时监测市场情绪变化，洞察资金动向</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={calculateCycle}
            disabled={calculating}
            variant="outline"
          >
            <Activity className={`mr-2 h-4 w-4 ${calculating ? 'animate-spin' : ''}`} />
            {calculating ? '计算中...' : '计算周期'}
          </Button>
          <Button onClick={refreshAll} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新数据
          </Button>
        </div>
      </div>

      {/* 信息提示 */}
      {infoMessage && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="py-4">
            <div className="flex items-center space-x-2 text-blue-800">
              <AlertCircle className="h-5 w-5" />
              <span>{infoMessage}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 错误提示 */}
      {error && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-yellow-800">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
              {error.includes('暂无') && (
                <Button
                  onClick={calculateCycle}
                  disabled={calculating}
                  size="sm"
                  variant="outline"
                >
                  <Activity className={`mr-2 h-3 w-3 ${calculating ? 'animate-spin' : ''}`} />
                  {calculating ? '计算中...' : '立即计算'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 情绪周期概览 */}
      {currentCycle && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">情绪阶段</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <Badge className={getStageColor(currentCycle.cycle_stage_cn)}>
                  {currentCycle.cycle_stage_cn}
                </Badge>
                <span className="text-2xl font-bold">{currentCycle.confidence_score.toFixed(0)}%</span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                持续 {currentCycle.stage_duration_days} 天
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">赚钱效应指数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <span className="text-3xl font-bold">{currentCycle.money_making_index.toFixed(1)}</span>
                <span className="text-sm text-muted-foreground">/100</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all"
                  style={{ width: `${currentCycle.money_making_index}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">涨停 / 跌停</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1">
                  <TrendingUp className="h-4 w-4 text-red-500" />
                  <span className="text-2xl font-bold text-red-500">
                    {currentCycle.limit_up_count}
                  </span>
                </div>
                <span className="text-muted-foreground">/</span>
                <div className="flex items-center space-x-1">
                  <TrendingDown className="h-4 w-4 text-green-500" />
                  <span className="text-2xl font-bold text-green-500">
                    {currentCycle.limit_down_count}
                  </span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                涨跌比: {currentCycle.limit_ratio.toFixed(2)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">连板高度</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <Activity className="h-6 w-6 text-purple-500" />
                <span className="text-3xl font-bold">{currentCycle.max_continuous_days}</span>
                <span className="text-sm text-muted-foreground">天</span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {currentCycle.max_continuous_count} 只股票
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 详细分析 */}
      {currentCycle?.analysis_result && (
        <Card>
          <CardHeader>
            <CardTitle>市场分析</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {currentCycle.analysis_result.stage_reason && (
              <div>
                <h4 className="font-semibold text-sm mb-1">阶段原因</h4>
                <p className="text-sm text-muted-foreground">{currentCycle.analysis_result.stage_reason}</p>
              </div>
            )}
            {currentCycle.analysis_result.risk_warning && (
              <div>
                <h4 className="font-semibold text-sm mb-1">风险提示</h4>
                <p className="text-sm text-yellow-700 dark:text-yellow-600">{currentCycle.analysis_result.risk_warning}</p>
              </div>
            )}
            {currentCycle.analysis_result.market_characteristics && (
              <div>
                <h4 className="font-semibold text-sm mb-2">市场特征</h4>
                <div className="flex flex-wrap gap-2">
                  {currentCycle.analysis_result.market_characteristics.map((char: string, idx: number) => (
                    <Badge key={idx} variant="outline">{char}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="institution" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="institution">机构动向</TabsTrigger>
          <TabsTrigger value="hotmoney">游资打板</TabsTrigger>
          <TabsTrigger value="ranking">活跃度排行</TabsTrigger>
        </TabsList>

        {/* 机构净买入排行 */}
        <TabsContent value="institution">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Building2 className="h-5 w-5" />
                <span>机构净买入TOP3</span>
              </CardTitle>
              <CardDescription>机构资金流向分析</CardDescription>
            </CardHeader>
            <CardContent>
              {institutionTop.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">暂无数据</p>
              ) : (
                <div className="space-y-4">
                  {institutionTop.map((stock, idx) => (
                    <div key={stock.stock_code} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <Badge variant="outline">#{idx + 1}</Badge>
                            <span className="font-semibold">{stock.stock_name}</span>
                            <span className="text-muted-foreground">({stock.stock_code})</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{stock.reason}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-red-500">
                            {formatAmount(stock.net_buy_amount)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {stock.institution_count}家机构
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 space-y-1">
                        {stock.institution_seats.map((seat, seatIdx) => (
                          <div key={seatIdx} className="flex justify-between text-sm">
                            <span className="text-muted-foreground truncate max-w-xs">{seat.seat_name}</span>
                            <span className="font-medium">
                              {formatAmount(seat.buy_amount)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 游资打板排行 */}
        <TabsContent value="hotmoney">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Users className="h-5 w-5" />
                <span>一线顶级游资打板TOP10</span>
              </CardTitle>
              <CardDescription>顶级游资操作跟踪</CardDescription>
            </CardHeader>
            <CardContent>
              {hotMoneyTop.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">暂无数据</p>
              ) : (
                <div className="space-y-3">
                  {hotMoneyTop.map((stock, idx) => (
                    <div key={stock.stock_code} className="border rounded-lg p-3">
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline">#{idx + 1}</Badge>
                          <span className="font-semibold">{stock.stock_name}</span>
                          {stock.is_limit_up && (
                            <Badge variant="destructive">涨停</Badge>
                          )}
                        </div>
                        <div className="text-right">
                          <div className="font-bold">
                            {formatAmount(stock.total_buy_amount)}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {stock.hot_money_count}个游资
                          </div>
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {stock.hot_money_seats.slice(0, 3).map((seat, seatIdx) => (
                          <Badge key={seatIdx} variant="secondary" className="text-xs">
                            {seat.seat_label}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 游资活跃度排行 */}
        <TabsContent value="ranking">
          <Card>
            <CardHeader>
              <CardTitle>游资活跃度排行榜（近30天）</CardTitle>
              <CardDescription>基于上榜次数、累计金额、胜率综合评分</CardDescription>
            </CardHeader>
            <CardContent>
              {hotMoneyRanking.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">暂无数据</p>
              ) : (
                <div className="space-y-2">
                  {hotMoneyRanking.map((seat, idx) => (
                    <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div className="flex items-center space-x-3 flex-1 min-w-0">
                        <Badge variant={idx < 3 ? "default" : "outline"} className="shrink-0">
                          #{idx + 1}
                        </Badge>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{seat.seat_label}</span>
                            {seat.city && <span className="text-sm text-muted-foreground">{seat.city}</span>}
                          </div>
                          <div className="text-xs text-muted-foreground truncate">
                            {seat.seat_name}
                          </div>
                        </div>
                      </div>
                      <div className="text-right shrink-0 ml-4">
                        <div className="font-semibold">
                          {seat.activity_score?.toFixed(1)}分
                        </div>
                        <div className="text-xs text-muted-foreground">
                          上榜{seat.appearance_count}次
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
