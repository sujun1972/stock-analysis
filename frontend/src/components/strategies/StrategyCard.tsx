'use client'

import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import type { SelectorInfo, EntryInfo, ExitInfo } from '@/lib/three-layer'

export type StrategyComponent = (SelectorInfo | EntryInfo | ExitInfo) & {
  layer: 'selector' | 'entry' | 'exit'
}

interface StrategyCardProps {
  component: StrategyComponent
}

const layerConfig = {
  selector: {
    label: '选股器',
    color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
    icon: '🎯',
  },
  entry: {
    label: '入场策略',
    color: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    icon: '📈',
  },
  exit: {
    label: '退出策略',
    color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
    icon: '📉',
  },
}

const categoryConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  momentum: { label: '动量', variant: 'default' },
  reversal: { label: '反转', variant: 'secondary' },
  ml: { label: '机器学习', variant: 'default' },
  external: { label: '外部信号', variant: 'outline' },
  technical: { label: '技术指标', variant: 'default' },
  breakout: { label: '突破', variant: 'secondary' },
  oversold: { label: '超卖', variant: 'outline' },
  immediate: { label: '即时', variant: 'secondary' },
  stop_loss: { label: '止损', variant: 'default' },
  atr: { label: 'ATR', variant: 'secondary' },
  trend: { label: '趋势', variant: 'outline' },
  fixed: { label: '固定周期', variant: 'outline' },
}

function getCategoryFromId(id: string): string {
  if (id.includes('momentum')) return 'momentum'
  if (id.includes('reversal')) return 'reversal'
  if (id.includes('ml')) return 'ml'
  if (id.includes('external')) return 'external'
  if (id.includes('breakout')) return 'breakout'
  if (id.includes('oversold')) return 'oversold'
  if (id.includes('immediate')) return 'immediate'
  if (id.includes('stop_loss') || id.includes('stop-loss')) return 'stop_loss'
  if (id.includes('atr')) return 'atr'
  if (id.includes('trend')) return 'trend'
  if (id.includes('fixed')) return 'fixed'
  return 'technical'
}

export function StrategyCard({ component }: StrategyCardProps) {
  const layerInfo = layerConfig[component.layer]
  const category = getCategoryFromId(component.id)
  const categoryInfo = categoryConfig[category] || categoryConfig.technical

  return (
    <Card className="h-full flex flex-col transition-all hover:shadow-lg hover:border-primary/50">
      <CardHeader>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{layerInfo.icon}</span>
            <Badge className={layerInfo.color} variant="outline">
              {layerInfo.label}
            </Badge>
          </div>
          <Badge variant={categoryInfo.variant}>{categoryInfo.label}</Badge>
        </div>
        <CardTitle className="text-xl">{component.name}</CardTitle>
        <CardDescription className="line-clamp-2">
          {component.description}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1">
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">版本</p>
            <p className="text-sm">{component.version}</p>
          </div>

          <div>
            <p className="text-sm font-medium text-muted-foreground mb-1">参数数量</p>
            <p className="text-sm">
              {component.parameters.length > 0
                ? `${component.parameters.length} 个参数`
                : '无需配置参数'}
            </p>
          </div>

          {component.parameters.length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">主要参数</p>
              <div className="flex flex-wrap gap-1">
                {component.parameters.slice(0, 3).map((param) => (
                  <Badge key={param.name} variant="outline" className="text-xs">
                    {param.label}
                  </Badge>
                ))}
                {component.parameters.length > 3 && (
                  <Badge variant="outline" className="text-xs">
                    +{component.parameters.length - 3}
                  </Badge>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="gap-2 pt-4">
        <Button variant="outline" size="sm" asChild className="flex-1">
          <Link href={`/strategies/${component.id}`}>
            查看详情
          </Link>
        </Button>
        <Button size="sm" asChild className="flex-1">
          <Link href={`/backtest/three-layer?${component.layer}=${component.id}`}>
            立即回测
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
