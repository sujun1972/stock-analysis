'use client'

import { useState, useMemo } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Download, TrendingUp, TrendingDown } from 'lucide-react'
import type { PositionRecord, PositionStats } from '@/lib/position-analysis'
import { calculatePositionStats } from '@/lib/position-analysis'

interface PositionDetailsTableProps {
  positions: PositionRecord[]
}

/**
 * 持仓明细表格组件
 * 展示每笔持仓的买入/卖出信息、持仓时间和收益率
 */
export function PositionDetailsTable({ positions }: PositionDetailsTableProps) {
  const [showAll, setShowAll] = useState(false)
  const [sortBy, setSortBy] = useState<'date' | 'return' | 'holding'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // 计算统计数据
  const stats: PositionStats = useMemo(() => {
    return calculatePositionStats(positions)
  }, [positions])

  // 排序后的持仓记录
  const sortedPositions = useMemo(() => {
    const sorted = [...positions]

    sorted.sort((a, b) => {
      let comparison = 0

      if (sortBy === 'date') {
        comparison = new Date(a.sellDate).getTime() - new Date(b.sellDate).getTime()
      } else if (sortBy === 'return') {
        comparison = a.returnRate - b.returnRate
      } else if (sortBy === 'holding') {
        comparison = a.holdingDays - b.holdingDays
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    return sorted
  }, [positions, sortBy, sortOrder])

  const displayPositions = showAll ? sortedPositions : sortedPositions.slice(0, 10)

  // 切换排序
  const handleSort = (key: 'date' | 'return' | 'holding') => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('desc')
    }
  }

  // 导出CSV
  const handleExportCSV = () => {
    const csvContent = [
      ['股票代码', '买入日期', '卖出日期', '买入价格', '卖出价格', '数量', '持仓天数', '收益率(%)', '盈亏金额'],
      ...positions.map(p => [
        p.stockCode,
        p.buyDate,
        p.sellDate,
        p.buyPrice.toFixed(2),
        p.sellPrice.toFixed(2),
        p.shares.toString(),
        p.holdingDays.toString(),
        (p.returnRate * 100).toFixed(2),
        p.profit.toFixed(2)
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `positions_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>持仓明细</CardTitle>
          <CardDescription>暂无持仓记录</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>持仓明细</CardTitle>
            <CardDescription>
              共 {positions.length} 笔交易，胜率 {(stats.winRate * 100).toFixed(2)}%
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" className="gap-2" onClick={handleExportCSV}>
            <Download className="h-4 w-4" />
            导出CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 持仓统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">总持仓数</p>
            <p className="text-2xl font-bold">{stats.totalPositions}</p>
          </div>
          <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
              <TrendingUp className="h-4 w-4" />
              <span>盈利笔数</span>
            </div>
            <p className="text-2xl font-bold text-green-700 dark:text-green-300">
              {stats.winningPositions}
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              平均: {(stats.avgWinReturn * 100).toFixed(2)}%
            </p>
          </div>
          <div className="p-4 bg-red-50 dark:bg-red-950 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-red-700 dark:text-red-300">
              <TrendingDown className="h-4 w-4" />
              <span>亏损笔数</span>
            </div>
            <p className="text-2xl font-bold text-red-700 dark:text-red-300">
              {stats.losingPositions}
            </p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
              平均: {(stats.avgLossReturn * 100).toFixed(2)}%
            </p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">平均持仓</p>
            <p className="text-2xl font-bold">{stats.avgHoldingDays.toFixed(1)} 天</p>
            <p className="text-xs text-muted-foreground mt-1">
              平均收益: {(stats.avgReturn * 100).toFixed(2)}%
            </p>
          </div>
        </div>

        {/* 持仓明细表格 */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>股票代码</TableHead>
                <TableHead>买入日期</TableHead>
                <TableHead>卖出日期</TableHead>
                <TableHead className="text-right">买入价格</TableHead>
                <TableHead className="text-right">卖出价格</TableHead>
                <TableHead className="text-right">数量</TableHead>
                <TableHead
                  className="text-right cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('holding')}
                >
                  持仓天数 {sortBy === 'holding' && (sortOrder === 'asc' ? '↑' : '↓')}
                </TableHead>
                <TableHead
                  className="text-right cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('return')}
                >
                  收益率 {sortBy === 'return' && (sortOrder === 'asc' ? '↑' : '↓')}
                </TableHead>
                <TableHead className="text-right">盈亏金额</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayPositions.map((position, idx) => (
                <TableRow key={idx}>
                  <TableCell className="font-mono font-semibold">
                    {position.stockCode}
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {position.buyDate}
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {position.sellDate}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    ¥{position.buyPrice.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    ¥{position.sellPrice.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {position.shares}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {position.holdingDays} 天
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold">
                    <span className={position.returnRate >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {(position.returnRate * 100).toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold">
                    <span className={position.profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {position.profit >= 0 ? '+' : ''}¥{position.profit.toFixed(2)}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* 查看全部按钮 */}
        {positions.length > 10 && (
          <div className="text-center">
            <Button
              variant="outline"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? '收起' : `查看全部 ${positions.length} 笔交易`}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
