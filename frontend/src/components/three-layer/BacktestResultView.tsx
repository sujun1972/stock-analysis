'use client'

import type { BacktestResult } from '@/lib/three-layer-types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import EquityCurveChart from '@/components/EquityCurveChart'
import PerformanceMetrics from '@/components/PerformanceMetrics'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Download, Share2, Save } from 'lucide-react'
import { useState } from 'react'

interface BacktestResultViewProps {
  result: BacktestResult
}

export function BacktestResultView({ result }: BacktestResultViewProps) {
  const [showAllTrades, setShowAllTrades] = useState(false)

  if (!result.data) {
    return null
  }

  const { data } = result
  const displayTrades = showAllTrades ? data.trades : data.trades.slice(0, 10)

  // 导出CSV功能
  const handleExportCSV = () => {
    const csvContent = [
      ['日期', '操作', '股票代码', '价格', '数量', '金额'],
      ...data.trades.map(t => [
        t.date,
        t.action === 'buy' ? '买入' : '卖出',
        t.stock_code,
        t.price.toFixed(2),
        t.shares.toString(),
        (t.price * t.shares).toFixed(2)
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `backtest_trades_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
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
            <Button variant="outline" size="sm" className="gap-2">
              <Save className="h-4 w-4" />
              保存到历史
            </Button>
            <Button variant="outline" size="sm" className="gap-2">
              <Share2 className="h-4 w-4" />
              分享结果
            </Button>
            <Button variant="outline" size="sm" className="gap-2" onClick={handleExportCSV}>
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

      {/* 净值曲线 */}
      <Card>
        <CardHeader>
          <CardTitle>净值曲线</CardTitle>
          <CardDescription>策略净值随时间的变化</CardDescription>
        </CardHeader>
        <CardContent>
          <EquityCurveChart
            strategyData={data.daily_portfolio.map(p => ({
              date: p.date,
              value: p.value,
            }))}
            title="策略净值曲线"
          />
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

      {/* 交易记录 */}
      <Card>
        <CardHeader>
          <CardTitle>交易记录</CardTitle>
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
