import { Metadata } from 'next'
import { StrategyList } from '@/components/strategies/StrategyList'

export const metadata: Metadata = {
  title: '策略中心 | Stock Analysis',
  description: '浏览和探索所有可用的选股器、入场策略和退出策略组件',
}

export default function StrategiesPage() {
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">策略中心</h1>
          <p className="text-muted-foreground">
            浏览所有可用的策略组件，包括4个选股器、3个入场策略和4个退出策略
          </p>
        </div>

        {/* 说明卡片 */}
        <div className="rounded-lg border bg-muted/50 p-4">
          <h3 className="font-semibold mb-2">策略组件说明</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm text-muted-foreground">
            <div>
              <strong className="text-foreground">选股器（4个）</strong>
              <p className="mt-1">从全市场筛选候选股票，支持动量、反转、机器学习等多种选股方法</p>
            </div>
            <div>
              <strong className="text-foreground">入场策略（3个）</strong>
              <p className="mt-1">决定何时买入候选股票，包括立即入场、均线突破、RSI超卖等</p>
            </div>
            <div>
              <strong className="text-foreground">退出策略（4个）</strong>
              <p className="mt-1">管理持仓并决定何时卖出，提供固定止损、ATR止损、趋势退出等方式</p>
            </div>
          </div>
        </div>

        {/* 策略列表组件 */}
        <StrategyList />
      </div>
    </div>
  )
}
