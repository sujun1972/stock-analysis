'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import type { SelectorInfo, EntryInfo, ExitInfo } from '@/lib/three-layer'
import Link from 'next/link'

type StrategyComponent = (SelectorInfo | EntryInfo | ExitInfo) & {
  layer: 'selector' | 'entry' | 'exit'
}

interface UsageGuideProps {
  component: StrategyComponent
}

const generateStrategyExample = (component: StrategyComponent): string => {
  const layer = component.layer
  const params: Record<string, any> = {}

  // 生成参数示例
  component.parameters.forEach((param) => {
    params[param.name] = param.default
  })

  // 根据层级生成不同的示例
  if (layer === 'selector') {
    return `// 使用 ${component.name}
const strategy = {
  selector: {
    id: '${component.id}',
    params: ${JSON.stringify(params, null, 6)}
  },
  entry: {
    id: 'immediate',  // 立即入场
    params: {}
  },
  exit: {
    id: 'fixed_stop_loss',  // 固定止损
    params: {
      stop_loss_pct: -5.0
    }
  },
  stock_codes: ['600000.SH', '000001.SZ'],
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  rebalance_freq: 'W'  // 周频调仓
}`
  }

  if (layer === 'entry') {
    return `// 使用 ${component.name}
const strategy = {
  selector: {
    id: 'momentum',  // 动量选股
    params: {
      lookback_period: 20,
      top_n: 50
    }
  },
  entry: {
    id: '${component.id}',
    params: ${JSON.stringify(params, null, 6)}
  },
  exit: {
    id: 'fixed_stop_loss',  // 固定止损
    params: {
      stop_loss_pct: -5.0
    }
  },
  stock_codes: ['600000.SH', '000001.SZ'],
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  rebalance_freq: 'W'
}`
  }

  // exit layer
  return `// 使用 ${component.name}
const strategy = {
  selector: {
    id: 'momentum',  // 动量选股
    params: {
      lookback_period: 20,
      top_n: 50
    }
  },
  entry: {
    id: 'immediate',  // 立即入场
    params: {}
  },
  exit: {
    id: '${component.id}',
    params: ${JSON.stringify(params, null, 6)}
  },
  stock_codes: ['600000.SH', '000001.SZ'],
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  rebalance_freq: 'W'
}`
}

const generateApiExample = (component: StrategyComponent): string => {
  return `// API调用示例
import { threeLayerApi } from '@/lib/three-layer'

// 1. 获取${component.name}详情
const component = await threeLayerApi.get${
    component.layer === 'selector' ? 'Selector' : component.layer === 'entry' ? 'Entry' : 'Exit'
  }ById('${component.id}')

console.log(component.name)         // ${component.name}
console.log(component.description)  // ${component.description}
console.log(component.parameters)   // 参数定义数组

// 2. 验证策略配置
const config = {
  selector_id: '${component.layer === 'selector' ? component.id : 'momentum'}',
  selector_params: ${component.layer === 'selector' ? '{ /* 参数 */ }' : '{ lookback_period: 20 }'},
  entry_id: '${component.layer === 'entry' ? component.id : 'immediate'}',
  entry_params: ${component.layer === 'entry' ? '{ /* 参数 */ }' : '{}'},
  exit_id: '${component.layer === 'exit' ? component.id : 'fixed_stop_loss'}',
  exit_params: ${component.layer === 'exit' ? '{ /* 参数 */ }' : '{ stop_loss_pct: -5.0 }'},
  stock_codes: ['600000.SH'],
  start_date: '2024-01-01',
  end_date: '2024-12-31'
}

const validation = await threeLayerApi.validateStrategy(config)
if (validation.valid) {
  // 3. 运行回测
  const result = await threeLayerApi.runBacktest(config)
  console.log(result.data.total_return)   // 总收益率
  console.log(result.data.sharpe_ratio)   // 夏普比率
}
`
}

export function UsageGuide({ component }: UsageGuideProps) {
  const [copiedStrategy, setCopiedStrategy] = useState(false)
  const [copiedApi, setCopiedApi] = useState(false)

  const strategyExample = generateStrategyExample(component)
  const apiExample = generateApiExample(component)

  const handleCopy = async (text: string, type: 'strategy' | 'api') => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === 'strategy') {
        setCopiedStrategy(true)
        setTimeout(() => setCopiedStrategy(false), 2000)
      } else {
        setCopiedApi(true)
        setTimeout(() => setCopiedApi(false), 2000)
      }
      toast.success('代码已复制到剪贴板')
    } catch (error) {
      toast.error('复制失败')
    }
  }

  const layerNames = {
    selector: '选股器',
    entry: '入场策略',
    exit: '退出策略',
  }

  return (
    <div className="space-y-6">
      {/* 快速开始 */}
      <Card>
        <CardHeader>
          <CardTitle>快速开始</CardTitle>
          <CardDescription>三个步骤开始使用 {component.name}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                1
              </div>
              <div className="space-y-1">
                <p className="font-medium">理解组件功能</p>
                <p className="text-sm text-muted-foreground">
                  阅读&quot;概览&quot;标签页，了解{component.name}的作用、适用场景和风险等级
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                2
              </div>
              <div className="space-y-1">
                <p className="font-medium">配置参数</p>
                <p className="text-sm text-muted-foreground">
                  查看&quot;参数配置&quot;标签页，了解每个参数的含义和取值范围，根据需要调整参数
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                3
              </div>
              <div className="space-y-1">
                <p className="font-medium">运行回测</p>
                <p className="text-sm text-muted-foreground">
                  点击&quot;立即回测&quot;按钮，在三层回测页面组合此组件与其他组件，运行完整回测
                </p>
              </div>
            </div>

            <div className="pt-4">
              <Button asChild>
                <Link href={`/backtest/three-layer?${component.layer}=${component.id}`}>
                  立即回测
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 策略配置示例 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>策略配置示例</CardTitle>
              <CardDescription>
                如何在策略配置中使用 {component.name}
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleCopy(strategyExample, 'strategy')}
            >
              {copiedStrategy ? (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  已复制
                </>
              ) : (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  复制代码
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
            <code className="text-muted-foreground">{strategyExample}</code>
          </pre>
        </CardContent>
      </Card>

      {/* API调用示例 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>API 调用示例</CardTitle>
              <CardDescription>
                如何通过 API 使用 {component.name}
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleCopy(apiExample, 'api')}
            >
              {copiedApi ? (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  已复制
                </>
              ) : (
                <>
                  <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  复制代码
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
            <code className="text-muted-foreground">{apiExample}</code>
          </pre>
        </CardContent>
      </Card>

      {/* 组合建议 */}
      <Card>
        <CardHeader>
          <CardTitle>组合建议</CardTitle>
          <CardDescription>
            推荐与 {component.name} 配合使用的组件
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {component.layer === 'selector' && (
              <>
                <div>
                  <p className="text-sm font-medium mb-2">推荐入场策略</p>
                  <div className="flex flex-wrap gap-2">
                    {component.id.includes('momentum') && (
                      <>
                        <Badge variant="outline">立即入场 (immediate)</Badge>
                        <Badge variant="outline">均线突破 (ma_breakout)</Badge>
                      </>
                    )}
                    {component.id.includes('reversal') && (
                      <>
                        <Badge variant="outline">RSI超卖 (rsi_oversold)</Badge>
                        <Badge variant="outline">立即入场 (immediate)</Badge>
                      </>
                    )}
                    {!component.id.includes('momentum') && !component.id.includes('reversal') && (
                      <>
                        <Badge variant="outline">立即入场 (immediate)</Badge>
                        <Badge variant="outline">均线突破 (ma_breakout)</Badge>
                        <Badge variant="outline">RSI超卖 (rsi_oversold)</Badge>
                      </>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">推荐退出策略</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">固定止损 (fixed_stop_loss)</Badge>
                    <Badge variant="outline">ATR止损 (atr_stop)</Badge>
                    <Badge variant="outline">趋势退出 (trend_exit)</Badge>
                  </div>
                </div>
              </>
            )}

            {component.layer === 'entry' && (
              <>
                <div>
                  <p className="text-sm font-medium mb-2">推荐选股器</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">动量选股 (momentum)</Badge>
                    <Badge variant="outline">反转选股 (reversal)</Badge>
                    <Badge variant="outline">机器学习选股 (ml_selector)</Badge>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">推荐退出策略</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">固定止损 (fixed_stop_loss)</Badge>
                    <Badge variant="outline">ATR止损 (atr_stop)</Badge>
                  </div>
                </div>
              </>
            )}

            {component.layer === 'exit' && (
              <>
                <div>
                  <p className="text-sm font-medium mb-2">推荐选股器</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">动量选股 (momentum)</Badge>
                    <Badge variant="outline">反转选股 (reversal)</Badge>
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">推荐入场策略</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">立即入场 (immediate)</Badge>
                    <Badge variant="outline">均线突破 (ma_breakout)</Badge>
                  </div>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 常见问题 */}
      <Card>
        <CardHeader>
          <CardTitle>常见问题</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="font-medium text-sm mb-1">Q: 如何调整参数以提高收益？</p>
              <p className="text-sm text-muted-foreground">
                A: 建议先用默认参数回测，然后根据结果逐个调整参数。避免过度优化导致过拟合。
              </p>
            </div>

            <div>
              <p className="font-medium text-sm mb-1">Q: 这个{layerNames[component.layer]}能单独使用吗？</p>
              <p className="text-sm text-muted-foreground">
                A: 不能。三层架构要求必须同时选择选股器、入场策略和退出策略，才能组成完整的回测策略。
              </p>
            </div>

            <div>
              <p className="font-medium text-sm mb-1">Q: 如何选择合适的股票池？</p>
              <p className="text-sm text-muted-foreground">
                A: 建议从流动性好的大盘股开始测试（如沪深300成分股），验证策略有效性后再扩展到更大的股票池。
              </p>
            </div>

            <div>
              <p className="font-medium text-sm mb-1">Q: 回测结果准确吗？</p>
              <p className="text-sm text-muted-foreground">
                A: 回测使用真实历史数据，但不包含交易成本、滑点等因素。实盘收益通常会低于回测结果。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
