import { Metadata } from 'next'
import { ThreeLayerStrategyPanel } from '@/components/three-layer/ThreeLayerStrategyPanel'

export const metadata: Metadata = {
  title: '三层架构回测 | Stock Analysis',
  description: '灵活组合选股器、入场策略和退出策略，实现48种策略组合',
}

export default function ThreeLayerBacktestPage() {
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">三层架构回测</h1>
          <p className="text-muted-foreground">
            通过三层架构组合选股器、入场策略和退出策略，探索多达48种策略组合的回测效果
          </p>
        </div>

        {/* 说明卡片 */}
        <div className="rounded-lg border bg-muted/50 p-4">
          <h3 className="font-semibold mb-2">三层架构说明</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>
              <strong>第一层（选股器）</strong>: 从全市场筛选候选股票池，通常以周频或月频运行
            </li>
            <li>
              <strong>第二层（入场策略）</strong>: 在候选池中决定何时买入，以日频运行
            </li>
            <li>
              <strong>第三层（退出策略）</strong>: 管理持仓，决定何时卖出，以日频或实时运行
            </li>
          </ul>
        </div>

        {/* 主要内容 */}
        <ThreeLayerStrategyPanel />
      </div>
    </div>
  )
}
