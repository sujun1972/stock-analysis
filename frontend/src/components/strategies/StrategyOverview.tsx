'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { SelectorInfo, EntryInfo, ExitInfo } from '@/lib/three-layer'

type StrategyComponent = (SelectorInfo | EntryInfo | ExitInfo) & {
  layer: 'selector' | 'entry' | 'exit'
}

interface StrategyOverviewProps {
  component: StrategyComponent
}

const layerDescriptions = {
  selector: {
    title: '选股器组件',
    description: '选股器负责从全市场中筛选出候选股票池。它会根据设定的因子和条件，定期（周频或月频）选出最有潜力的股票。',
    useCases: [
      '动量策略：选出近期涨幅最大的股票',
      '反转策略：选出近期跌幅最大的股票',
      '机器学习：使用AI模型预测股票表现',
      '外部信号：接入第三方选股信号',
    ],
  },
  entry: {
    title: '入场策略组件',
    description: '入场策略决定何时买入选股器选出的候选股票。它会根据技术指标、价格形态等条件，在合适的时机触发买入信号。',
    useCases: [
      '立即入场：选出后立即买入',
      '均线突破：等待股价突破移动均线',
      'RSI超卖：等待超卖反弹机会',
      '突破新高：等待股价创新高',
    ],
  },
  exit: {
    title: '退出策略组件',
    description: '退出策略管理已持有的仓位，决定何时卖出股票。它会根据止损条件、持仓时间、趋势变化等因素，保护利润并控制风险。',
    useCases: [
      '固定止损：达到固定亏损比例时卖出',
      'ATR止损：基于波动率的动态止损',
      '趋势退出：趋势反转时卖出',
      '固定周期：持仓固定天数后卖出',
    ],
  },
}

const getRiskLevel = (component: StrategyComponent): { level: string; color: string; description: string } => {
  // 根据组件类型和ID判断风险等级
  const id = component.id.toLowerCase()

  if (component.layer === 'selector') {
    if (id.includes('ml') || id.includes('external')) {
      return {
        level: '中高',
        color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
        description: '依赖模型或外部信号，需要谨慎验证',
      }
    }
    if (id.includes('reversal')) {
      return {
        level: '中',
        color: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
        description: '反转策略存在一定风险，建议配合止损',
      }
    }
  }

  if (component.layer === 'exit') {
    if (id.includes('fixed_period')) {
      return {
        level: '中高',
        color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
        description: '固定周期可能错过最佳退出时机',
      }
    }
    if (id.includes('atr') || id.includes('stop_loss')) {
      return {
        level: '低',
        color: 'bg-green-500/10 text-green-700 dark:text-green-400',
        description: '止损策略能有效控制风险',
      }
    }
  }

  return {
    level: '中',
    color: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
    description: '正常风险水平，建议合理配置参数',
  }
}

export function StrategyOverview({ component }: StrategyOverviewProps) {
  const layerInfo = layerDescriptions[component.layer]
  const riskInfo = getRiskLevel(component)

  return (
    <div className="space-y-6">
      {/* 组件类型说明 */}
      <Card>
        <CardHeader>
          <CardTitle>{layerInfo.title}</CardTitle>
          <CardDescription>{layerInfo.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p className="text-sm font-medium">典型应用场景：</p>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              {layerInfo.useCases.map((useCase, index) => (
                <li key={index}>{useCase}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* 详细信息 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">组件ID</p>
              <code className="text-sm bg-muted px-2 py-1 rounded">{component.id}</code>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">组件名称</p>
              <p className="text-sm">{component.name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">版本号</p>
              <Badge variant="secondary">{component.version}</Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">参数数量</p>
              <p className="text-sm">
                {component.parameters.length > 0
                  ? `${component.parameters.length} 个可配置参数`
                  : '无需配置参数，开箱即用'}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 风险提示 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">风险评估</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">风险等级</p>
              <Badge className={riskInfo.color} variant="outline">
                {riskInfo.level}风险
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">风险说明</p>
              <p className="text-sm text-muted-foreground">{riskInfo.description}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">建议</p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>回测前请先理解策略逻辑</li>
                <li>使用真实数据验证参数有效性</li>
                <li>建议与其他组件组合使用</li>
                {component.layer === 'selector' && <li>选股器需要配合入场和退出策略</li>}
                {component.layer === 'exit' && <li>退出策略是风险控制的关键</li>}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 适用场景 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">适用场景</CardTitle>
          <CardDescription>该组件最适合以下市场环境和投资风格</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium mb-2">市场环境</p>
              <div className="flex flex-wrap gap-2">
                {component.id.includes('momentum') && (
                  <>
                    <Badge variant="outline">趋势市场</Badge>
                    <Badge variant="outline">牛市</Badge>
                  </>
                )}
                {component.id.includes('reversal') && (
                  <>
                    <Badge variant="outline">震荡市场</Badge>
                    <Badge variant="outline">均值回归</Badge>
                  </>
                )}
                {component.id.includes('ml') && (
                  <>
                    <Badge variant="outline">复杂市场</Badge>
                    <Badge variant="outline">多因子环境</Badge>
                  </>
                )}
                {component.id.includes('breakout') && (
                  <>
                    <Badge variant="outline">突破行情</Badge>
                    <Badge variant="outline">强势股</Badge>
                  </>
                )}
                {!component.id.includes('momentum') &&
                  !component.id.includes('reversal') &&
                  !component.id.includes('ml') &&
                  !component.id.includes('breakout') && (
                    <>
                      <Badge variant="outline">通用市场</Badge>
                      <Badge variant="outline">各类行情</Badge>
                    </>
                  )}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium mb-2">投资风格</p>
              <div className="flex flex-wrap gap-2">
                {component.layer === 'selector' && component.id.includes('momentum') && (
                  <>
                    <Badge variant="outline">趋势跟随</Badge>
                    <Badge variant="outline">中短期</Badge>
                  </>
                )}
                {component.layer === 'selector' && component.id.includes('reversal') && (
                  <>
                    <Badge variant="outline">反向投资</Badge>
                    <Badge variant="outline">短期交易</Badge>
                  </>
                )}
                {component.layer === 'exit' && component.id.includes('stop_loss') && (
                  <>
                    <Badge variant="outline">风险厌恶</Badge>
                    <Badge variant="outline">保守型</Badge>
                  </>
                )}
                {component.layer === 'exit' && component.id.includes('trend') && (
                  <>
                    <Badge variant="outline">趋势追随</Badge>
                    <Badge variant="outline">中长期持仓</Badge>
                  </>
                )}
                {!component.id.includes('momentum') &&
                  !component.id.includes('reversal') &&
                  !component.id.includes('stop_loss') &&
                  !component.id.includes('trend') && (
                    <>
                      <Badge variant="outline">灵活配置</Badge>
                      <Badge variant="outline">适应性强</Badge>
                    </>
                  )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 完整描述 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">完整描述</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {component.description}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
