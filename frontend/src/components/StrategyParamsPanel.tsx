'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronDown, ChevronUp } from 'lucide-react'

interface StrategyParameter {
  name: string
  label: string
  type: 'integer' | 'float' | 'boolean' | 'select'
  default: any
  min_value?: number
  max_value?: number
  step?: number
  options?: Array<{ value: any; label: string }>
  description: string
  category: string
}

interface StrategyMetadata {
  id: string
  name: string
  description: string
  version: string
  parameters: StrategyParameter[]
}

interface StrategyParamsPanelProps {
  strategyId: string
  onParamsChange: (params: Record<string, any>) => void
  onApply?: () => void
  isInDialog?: boolean // 是否在对话框中显示（影响展开/折叠行为）
}

export default function StrategyParamsPanel({
  strategyId,
  onParamsChange,
  onApply,
  isInDialog = false
}: StrategyParamsPanelProps) {
  const [metadata, setMetadata] = useState<StrategyMetadata | null>(null)
  const [params, setParams] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['趋势', '超买超卖']))

  // 加载策略元数据
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        setLoading(true)
        const response = await apiClient.getStrategyMetadata(strategyId)

        if (response.data) {
          setMetadata(response.data)

          // 如果在对话框中，默认展开所有分类
          if (isInDialog) {
            const allCategories = new Set<string>()
            response.data.parameters.forEach((param: StrategyParameter) => {
              allCategories.add(param.category)
            })
            setExpandedCategories(allCategories)
          }

          // 初始化参数为默认值
          const defaultParams: Record<string, any> = {}
          response.data.parameters.forEach((param: StrategyParameter) => {
            defaultParams[param.name] = param.default
          })
          setParams(defaultParams)
          onParamsChange(defaultParams)
        }
      } catch (error) {
        console.error('获取策略元数据失败:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchMetadata()
    // onParamsChange 会导致无限循环，这里不添加到依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategyId, isInDialog])

  // 参数值变化处理
  const handleParamChange = (name: string, value: any) => {
    const newParams = { ...params, [name]: value }
    setParams(newParams)
    onParamsChange(newParams)
  }

  // 重置为默认值
  const handleReset = () => {
    if (!metadata) return

    const defaultParams: Record<string, any> = {}
    metadata.parameters.forEach(param => {
      defaultParams[param.name] = param.default
    })
    setParams(defaultParams)
    onParamsChange(defaultParams)
  }

  // 切换分类折叠状态
  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }

  // 渲染单个参数输入组件
  const renderParamInput = (param: StrategyParameter) => {
    const value = params[param.name] ?? param.default

    switch (param.type) {
      case 'integer':
        return (
          <div key={param.name} className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor={param.name} className="flex-1">
                {param.label}
              </Label>
              <Input
                id={param.name}
                type="number"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseInt(e.target.value) || param.default)}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 1}
                className="w-20"
              />
            </div>
            {param.min_value !== undefined && param.max_value !== undefined && (
              <input
                type="range"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseInt(e.target.value))}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 1}
                className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
              />
            )}
            <p className="text-xs text-muted-foreground">{param.description}</p>
          </div>
        )

      case 'float':
        return (
          <div key={param.name} className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor={param.name} className="flex-1">
                {param.label}
              </Label>
              <Input
                id={param.name}
                type="number"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseFloat(e.target.value) || param.default)}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 0.1}
                className="w-24"
              />
            </div>
            {param.min_value !== undefined && param.max_value !== undefined && (
              <input
                type="range"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseFloat(e.target.value))}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 0.1}
                className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
              />
            )}
            <p className="text-xs text-muted-foreground">{param.description}</p>
          </div>
        )

      case 'boolean':
        return (
          <div key={param.name} className="flex items-center justify-between gap-3">
            <div className="flex-1 space-y-0.5">
              <Label htmlFor={param.name}>{param.label}</Label>
              <p className="text-xs text-muted-foreground">{param.description}</p>
            </div>
            <Switch
              id={param.name}
              checked={value}
              onCheckedChange={(checked) => handleParamChange(param.name, checked)}
            />
          </div>
        )

      case 'select':
        return (
          <div key={param.name} className="space-y-2">
            <Label htmlFor={param.name}>{param.label}</Label>
            <Select
              value={String(value)}
              onValueChange={(newValue) => handleParamChange(param.name, newValue)}
            >
              <SelectTrigger id={param.name}>
                <SelectValue placeholder={`选择${param.label}`} />
              </SelectTrigger>
              <SelectContent>
                {param.options?.map(option => (
                  <SelectItem key={option.value} value={String(option.value)}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{param.description}</p>
          </div>
        )

      default:
        return null
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <span className="ml-3 text-muted-foreground">加载策略参数...</span>
      </div>
    )
  }

  if (!metadata) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-destructive">无法加载策略参数</p>
      </div>
    )
  }

  // 按分类组织参数
  const paramsByCategory: Record<string, StrategyParameter[]> = {}
  metadata.parameters.forEach(param => {
    if (!paramsByCategory[param.category]) {
      paramsByCategory[param.category] = []
    }
    paramsByCategory[param.category].push(param)
  })

  // 对话框中的简化布局
  if (isInDialog) {
    return (
      <div className="space-y-4 sm:space-y-6">
        {/* 重置按钮 */}
        <div className="flex justify-end">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
          >
            重置为默认值
          </Button>
        </div>

        {/* 参数配置区域 - 两列布局（大屏幕） */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
          {Object.entries(paramsByCategory).map(([category, categoryParams]) => (
            <Card key={category}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm sm:text-base">{category}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 sm:space-y-4">
                {categoryParams.map(param => renderParamInput(param))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  // 原有的完整布局（用于非对话框场景）
  return (
    <Card>
      <CardHeader>
        <CardTitle>{metadata.name}</CardTitle>
        <CardDescription>{metadata.description}</CardDescription>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-muted-foreground">
            版本 {metadata.version}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
          >
            重置为默认值
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 max-h-[600px] overflow-y-auto">
        {Object.entries(paramsByCategory).map(([category, categoryParams]) => (
          <div key={category} className="border rounded-lg overflow-hidden">
            <Button
              type="button"
              variant="ghost"
              onClick={() => toggleCategory(category)}
              className="w-full justify-between h-auto py-3 px-4 hover:bg-accent"
            >
              <span className="font-medium">{category}</span>
              {expandedCategories.has(category) ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>

            {expandedCategories.has(category) && (
              <div className="p-4 space-y-4 border-t">
                {categoryParams.map(param => renderParamInput(param))}
              </div>
            )}
          </div>
        ))}
      </CardContent>

      {onApply && (
        <CardContent className="border-t pt-4">
          <Button
            type="button"
            onClick={onApply}
            className="w-full"
          >
            应用参数并回测
          </Button>
        </CardContent>
      )}
    </Card>
  )
}
