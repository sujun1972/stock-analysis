'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { SelectorInfo, EntryInfo, ExitInfo, ParameterDef } from '@/lib/three-layer'

type StrategyComponent = (SelectorInfo | EntryInfo | ExitInfo) & {
  layer: 'selector' | 'entry' | 'exit'
}

interface ParametersTableProps {
  component: StrategyComponent
}

const typeIcons: Record<string, string> = {
  integer: '🔢',
  float: '📊',
  boolean: '✅',
  select: '📋',
  string: '📝',
}

const typeLabels: Record<string, string> = {
  integer: '整数',
  float: '浮点数',
  boolean: '布尔值',
  select: '选项',
  string: '字符串',
}

const formatValue = (value: any, type: string): string => {
  if (value === null || value === undefined) {
    return '-'
  }

  if (type === 'boolean') {
    return value ? '是' : '否'
  }

  if (type === 'float' && typeof value === 'number') {
    return value.toFixed(2)
  }

  return String(value)
}

const formatRange = (param: ParameterDef): string => {
  if (param.type === 'boolean') {
    return '是/否'
  }

  if (param.type === 'select' && param.options) {
    return param.options.map(opt => opt.label).join(', ')
  }

  if (param.type === 'integer' || param.type === 'float') {
    if (param.min_value !== undefined && param.max_value !== undefined) {
      return `${param.min_value} ~ ${param.max_value}`
    }
    if (param.min_value !== undefined) {
      return `≥ ${param.min_value}`
    }
    if (param.max_value !== undefined) {
      return `≤ ${param.max_value}`
    }
  }

  return '-'
}

export function ParametersTable({ component }: ParametersTableProps) {
  if (component.parameters.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>参数配置</CardTitle>
          <CardDescription>该组件无需配置任何参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <svg
              className="mx-auto h-12 w-12 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium">无需配置</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              此组件开箱即用，无需调整任何参数。您可以直接在回测中使用。
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* 参数概览卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>参数概览</CardTitle>
          <CardDescription>
            该组件共有 {component.parameters.length} 个可配置参数，您可以根据需要调整这些参数以优化策略表现
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {component.parameters.map((param) => (
              <Badge key={param.name} variant="outline">
                {typeIcons[param.type]} {param.label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 参数详细表格 */}
      <Card>
        <CardHeader>
          <CardTitle>参数详情</CardTitle>
          <CardDescription>每个参数的详细说明和取值范围</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">参数名称</TableHead>
                  <TableHead className="w-[100px]">类型</TableHead>
                  <TableHead className="w-[120px]">默认值</TableHead>
                  <TableHead className="w-[150px]">取值范围</TableHead>
                  <TableHead>说明</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {component.parameters.map((param) => (
                  <TableRow key={param.name}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{param.label}</p>
                        <code className="text-xs text-muted-foreground">{param.name}</code>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {typeIcons[param.type]} {typeLabels[param.type]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {formatValue(param.default, param.type)}
                      </code>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {formatRange(param)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <p className="text-sm text-muted-foreground">
                        {param.description || '无额外说明'}
                      </p>
                      {param.step && (param.type === 'integer' || param.type === 'float') && (
                        <p className="text-xs text-muted-foreground mt-1">
                          步长: {param.step}
                        </p>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* 参数调优建议 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">参数调优建议</CardTitle>
          <CardDescription>如何调整参数以获得更好的回测效果</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-blue-500 mt-0.5">💡</span>
              <div>
                <p className="font-medium">从默认值开始</p>
                <p className="text-muted-foreground">
                  默认参数已经过基础测试，建议先用默认值运行回测，了解策略的基本表现
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">📊</span>
              <div>
                <p className="font-medium">逐个调整参数</p>
                <p className="text-muted-foreground">
                  每次只调整一个参数，观察对回测结果的影响，避免同时调整多个参数导致难以分析
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="text-orange-500 mt-0.5">⚠️</span>
              <div>
                <p className="font-medium">避免过度优化</p>
                <p className="text-muted-foreground">
                  不要为了追求完美的回测结果而过度调整参数，这可能导致过拟合，实盘表现不佳
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="text-purple-500 mt-0.5">🔄</span>
              <div>
                <p className="font-medium">多周期验证</p>
                <p className="text-muted-foreground">
                  在不同的时间周期（牛市、熊市、震荡市）测试参数的稳定性，确保策略的鲁棒性
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
