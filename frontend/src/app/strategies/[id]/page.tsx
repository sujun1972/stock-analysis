import { Metadata } from 'next'
import { StrategyDetail } from '@/components/strategies/StrategyDetail'

export const metadata: Metadata = {
  title: '策略详情 | Stock Analysis',
  description: '查看策略组件的详细信息、参数说明和使用示例',
}

interface StrategyDetailPageProps {
  params: {
    id: string
  }
}

export default function StrategyDetailPage({ params }: StrategyDetailPageProps) {
  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <StrategyDetail strategyId={params.id} />
    </div>
  )
}
