/**
 * LLM调用日志概览卡片
 * 展示7天内的总调用次数、成功率、Tokens消耗和总成本
 */

'use client'

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react'
import type { LLMSummary } from '@/lib/llm-logs-api'

interface LlmCallSummaryCardsProps {
  summary: LLMSummary
}

export function LlmCallSummaryCards({ summary }: LlmCallSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardDescription>总调用次数（7天）</CardDescription>
          <CardTitle className="text-3xl">{summary.overview.total_calls}</CardTitle>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardDescription>成功率</CardDescription>
          <CardTitle className="text-3xl flex items-center gap-2">
            {summary.overview.success_rate.toFixed(1)}%
            {summary.overview.success_rate >= 95 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : summary.overview.success_rate >= 80 ? (
              <Minus className="w-5 h-5 text-yellow-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </CardTitle>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardDescription>总消耗Tokens</CardDescription>
          <CardTitle className="text-3xl">{summary.overview.total_tokens.toLocaleString()}</CardTitle>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardDescription>总成本</CardDescription>
          <CardTitle className="text-3xl">${summary.overview.total_cost.toFixed(4)}</CardTitle>
        </CardHeader>
      </Card>
    </div>
  )
}
