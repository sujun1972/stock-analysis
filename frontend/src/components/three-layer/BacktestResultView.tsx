'use client'

import { useMemo, useState } from 'react'
import type { BacktestResult } from '@/lib/three-layer-types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import EquityCurveChart from '@/components/EquityCurveChart'
import PerformanceMetrics from '@/components/PerformanceMetrics'
import DrawdownChart from './DrawdownChart'
import { PositionDetailsTable } from './PositionDetailsTable'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Download, Share2, Save, Copy, CheckCircle2 } from 'lucide-react'
import { analyzePositions, calculateDrawdown } from '@/lib/position-analysis'
import { toast } from 'sonner'

interface BacktestResultViewProps {
  result: BacktestResult
  onSave?: () => void
}

export function BacktestResultView({ result, onSave }: BacktestResultViewProps) {
  const [showAllTrades, setShowAllTrades] = useState(false)

  // 计算持仓明细
  const positions = useMemo(() => {
    if (!result.data) return []
    return analyzePositions(result.data.trades)
  }, [result.data])

  // 计算回撤数据
  const drawdownData = useMemo(() => {
    if (!result.data) return []
    return calculateDrawdown(result.data.daily_portfolio)
  }, [result.data])

  if (!result.data) {
    return null
  }

  const { data } = result

  const displayTrades = showAllTrades ? data.trades : data.trades.slice(0, 10)

  // 导出完整报告（CSV格式）
  const handleExportReport = () => {
    const sections = []

    // 1. 绩效指标
    sections.push('=== 绩效指标 ===')
    sections.push('总收益率,' + (data.total_return * 100).toFixed(2) + '%')
    sections.push('年化收益率,' + (data.annualized_return * 100).toFixed(2) + '%')
    sections.push('夏普比率,' + data.sharpe_ratio.toFixed(2))
    sections.push('最大回撤,' + (data.max_drawdown * 100).toFixed(2) + '%')
    sections.push('胜率,' + (data.win_rate * 100).toFixed(2) + '%')
    sections.push('总交易次数,' + data.total_trades)

    if (data.sortino_ratio) sections.push('索提诺比率,' + data.sortino_ratio.toFixed(2))
    if (data.calmar_ratio) sections.push('卡玛比率,' + data.calmar_ratio.toFixed(2))
    if (data.volatility) sections.push('波动率,' + (data.volatility * 100).toFixed(2) + '%')

    sections.push('')

    // 2. 净值曲线
    sections.push('=== 净值曲线 ===')
    sections.push('日期,净值')
    data.daily_portfolio.forEach(p => {
      sections.push(`${p.date},${p.value.toFixed(2)}`)
    })
    sections.push('')

    // 3. 交易记录
    sections.push('=== 交易记录 ===')
    sections.push('日期,操作,股票代码,价格,数量,金额')
    data.trades.forEach(t => {
      sections.push([
        t.date,
        t.action === 'buy' ? '买入' : '卖出',
        t.stock_code,
        t.price.toFixed(2),
        t.shares,
        (t.price * t.shares).toFixed(2)
      ].join(','))
    })

    const csvContent = sections.join('\n')
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `backtest_report_${new Date().toISOString().split('T')[0]}.csv`
    link.click()

    toast.success('报告已导出')
  }

  // 分享结果（复制链接到剪贴板）
  const handleShare = async () => {
    try {
      // 这里可以生成一个分享链接，暂时使用当前URL
      const shareUrl = window.location.href
      await navigator.clipboard.writeText(shareUrl)
      toast.success('链接已复制到剪贴板')
    } catch (error) {
      toast.error('复制失败，请手动复制链接')
    }
  }

  // 保存到历史
  const handleSave = () => {
    if (onSave) {
      onSave()
    } else {
      toast.info('保存功能即将推出（需要后端API支持）')
    }
  }

  return (
    <div className="space-y-6">
      {/* 操作按钮 */}
      <Card>
        <CardHeader>
          <CardTitle>回测结果</CardTitle>
          <CardDescription>查看详细的回测绩效指标、净值曲线和交易记录</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-2" onClick={handleSave}>
              <Save className="h-4 w-4" />
              保存到历史
            </Button>
            <Button variant="outline" size="sm" className="gap-2" onClick={handleShare}>
              <Share2 className="h-4 w-4" />
              分享结果
            </Button>
            <Button variant="outline" size="sm" className="gap-2" onClick={handleExportReport}>
              <Download className="h-4 w-4" />
              导出报告
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 绩效指标 */}
      <Card>
        <CardHeader>
          <CardTitle>绩效指标</CardTitle>
          <CardDescription>策略的关键风险收益指标</CardDescription>
        </CardHeader>
        <CardContent>
          <PerformanceMetrics
            metrics={{
              total_return: data.total_return,
              annualized_return: data.annualized_return,
              sharpe_ratio: data.sharpe_ratio,
              max_drawdown: data.max_drawdown,
              win_rate: data.win_rate,
              sortino_ratio: data.sortino_ratio,
              calmar_ratio: data.calmar_ratio,
              volatility: data.volatility,
              alpha: data.alpha,
              beta: data.beta,
            }}
            mode="multi"
          />
        </CardContent>
      </Card>

      {/* 净值曲线和回撤曲线 */}
      <Card>
        <CardHeader>
          <CardTitle>净值与回撤分析</CardTitle>
          <CardDescription>策略净值和回撤曲线</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="equity" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="equity">净值曲线</TabsTrigger>
              <TabsTrigger value="drawdown">回撤曲线</TabsTrigger>
            </TabsList>
            <TabsContent value="equity" className="mt-4">
              <EquityCurveChart
                strategyData={data.daily_portfolio.map(p => ({
                  date: p.date,
                  value: p.value,
                }))}
                title="策略净值曲线"
              />
            </TabsContent>
            <TabsContent value="drawdown" className="mt-4">
              <DrawdownChart
                data={drawdownData}
                maxDrawdown={data.max_drawdown}
                title="回撤曲线"
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* 交易统计 */}
      <Card>
        <CardHeader>
          <CardTitle>交易统计</CardTitle>
          <CardDescription>总交易次数: {data.total_trades}次</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">总交易次数</p>
              <p className="text-2xl font-bold">{data.total_trades}</p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">胜率</p>
              <p className="text-2xl font-bold text-green-600">
                {(data.win_rate * 100).toFixed(2)}%
              </p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">买入次数</p>
              <p className="text-2xl font-bold">
                {data.trades.filter(t => t.action === 'buy').length}
              </p>
            </div>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">卖出次数</p>
              <p className="text-2xl font-bold">
                {data.trades.filter(t => t.action === 'sell').length}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 持仓明细（配对的买入-卖出交易） */}
      <PositionDetailsTable positions={positions} />

      {/* 交易记录（原始交易流水） */}
      <Card>
        <CardHeader>
          <CardTitle>交易流水</CardTitle>
          <CardDescription>
            {showAllTrades ? `显示全部 ${data.trades.length} 条记录` : `显示前 10 条，共 ${data.trades.length} 条记录`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>日期</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>股票代码</TableHead>
                  <TableHead className="text-right">价格</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayTrades.map((trade, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-mono text-sm">
                      {trade.date}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          trade.action === 'buy'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        }`}
                      >
                        {trade.action === 'buy' ? '买入' : '卖出'}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono">{trade.stock_code}</TableCell>
                    <TableCell className="text-right font-mono">
                      ¥{trade.price.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {trade.shares}
                    </TableCell>
                    <TableCell className="text-right font-mono font-semibold">
                      ¥{(trade.price * trade.shares).toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {data.trades.length > 10 && (
            <div className="mt-4 text-center">
              <Button
                variant="outline"
                onClick={() => setShowAllTrades(!showAllTrades)}
              >
                {showAllTrades ? '收起' : `查看全部 ${data.trades.length} 条记录`}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
