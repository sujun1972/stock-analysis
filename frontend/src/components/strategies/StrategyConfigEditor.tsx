/**
 * 策略配置编辑器组件
 * 根据策略的 param_schema 动态生成表单字段
 */

'use client'

import { memo } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import type { StrategyTypeMeta } from '@/types/strategy'

interface StrategyConfigEditorProps {
  strategyType: string
  config: Record<string, any>
  schema: StrategyTypeMeta['param_schema']
  onChange: (config: Record<string, any>) => void
  readOnly?: boolean
}

const StrategyConfigEditor = memo(function StrategyConfigEditor({
  strategyType,
  config,
  schema,
  onChange,
  readOnly = false
}: StrategyConfigEditorProps) {
  const handleValueChange = (key: string, value: any) => {
    if (readOnly) return
    onChange({
      ...config,
      [key]: value
    })
  }

  const renderField = (key: string, paramConfig: any) => {
    const currentValue = config[key] !== undefined ? config[key] : paramConfig.default

    // 整数输入
    if (paramConfig.type === 'integer') {
      return (
        <div key={key} className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor={`param-${key}`} className="text-sm font-medium">
              {paramConfig.description || key}
            </Label>
            <span className="text-sm text-muted-foreground">{currentValue}</span>
          </div>
          {paramConfig.min !== undefined && paramConfig.max !== undefined ? (
            <Slider
              id={`param-${key}`}
              min={paramConfig.min}
              max={paramConfig.max}
              step={paramConfig.step || 1}
              value={[currentValue]}
              onValueChange={(values) => handleValueChange(key, values[0])}
              disabled={readOnly}
              className="w-full"
            />
          ) : (
            <Input
              id={`param-${key}`}
              type="number"
              value={currentValue}
              onChange={(e) => handleValueChange(key, parseInt(e.target.value) || paramConfig.default)}
              disabled={readOnly}
              min={paramConfig.min}
              max={paramConfig.max}
              step={paramConfig.step || 1}
            />
          )}
          {(paramConfig.min !== undefined || paramConfig.max !== undefined) && (
            <p className="text-xs text-muted-foreground">
              范围: {paramConfig.min ?? '-∞'} ~ {paramConfig.max ?? '+∞'}
            </p>
          )}
        </div>
      )
    }

    // 浮点数输入
    if (paramConfig.type === 'float') {
      return (
        <div key={key} className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor={`param-${key}`} className="text-sm font-medium">
              {paramConfig.description || key}
            </Label>
            <span className="text-sm text-muted-foreground">{currentValue}</span>
          </div>
          {paramConfig.min !== undefined && paramConfig.max !== undefined ? (
            <Slider
              id={`param-${key}`}
              min={paramConfig.min}
              max={paramConfig.max}
              step={paramConfig.step || 0.01}
              value={[currentValue]}
              onValueChange={(values) => handleValueChange(key, values[0])}
              disabled={readOnly}
              className="w-full"
            />
          ) : (
            <Input
              id={`param-${key}`}
              type="number"
              value={currentValue}
              onChange={(e) => handleValueChange(key, parseFloat(e.target.value) || paramConfig.default)}
              disabled={readOnly}
              min={paramConfig.min}
              max={paramConfig.max}
              step={paramConfig.step || 0.01}
            />
          )}
          {(paramConfig.min !== undefined || paramConfig.max !== undefined) && (
            <p className="text-xs text-muted-foreground">
              范围: {paramConfig.min ?? '-∞'} ~ {paramConfig.max ?? '+∞'}
            </p>
          )}
        </div>
      )
    }

    // 布尔值开关
    if (paramConfig.type === 'boolean') {
      return (
        <div key={key} className="flex items-center justify-between space-y-2">
          <div className="space-y-0.5">
            <Label htmlFor={`param-${key}`} className="text-sm font-medium">
              {paramConfig.description || key}
            </Label>
          </div>
          <Switch
            id={`param-${key}`}
            checked={currentValue}
            onCheckedChange={(checked) => handleValueChange(key, checked)}
            disabled={readOnly}
          />
        </div>
      )
    }

    // 下拉选择
    if (paramConfig.type === 'select' && paramConfig.options) {
      return (
        <div key={key} className="space-y-2">
          <Label htmlFor={`param-${key}`} className="text-sm font-medium">
            {paramConfig.description || key}
          </Label>
          <Select
            value={currentValue?.toString()}
            onValueChange={(value) => {
              // 尝试转换为原始类型
              const option = paramConfig.options.find((opt: any) => opt.value?.toString() === value)
              handleValueChange(key, option?.value ?? value)
            }}
            disabled={readOnly}
          >
            <SelectTrigger id={`param-${key}`}>
              <SelectValue placeholder="请选择" />
            </SelectTrigger>
            <SelectContent>
              {paramConfig.options.map((option: any, idx: number) => (
                <SelectItem key={idx} value={option.value?.toString()}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )
    }

    // 字符串输入
    if (paramConfig.type === 'string') {
      return (
        <div key={key} className="space-y-2">
          <Label htmlFor={`param-${key}`} className="text-sm font-medium">
            {paramConfig.description || key}
          </Label>
          <Input
            id={`param-${key}`}
            type="text"
            value={currentValue}
            onChange={(e) => handleValueChange(key, e.target.value)}
            disabled={readOnly}
          />
        </div>
      )
    }

    // 未知类型，使用文本输入
    return (
      <div key={key} className="space-y-2">
        <Label htmlFor={`param-${key}`} className="text-sm font-medium">
          {paramConfig.description || key}
        </Label>
        <Input
          id={`param-${key}`}
          type="text"
          value={JSON.stringify(currentValue)}
          onChange={(e) => {
            try {
              handleValueChange(key, JSON.parse(e.target.value))
            } catch {
              handleValueChange(key, e.target.value)
            }
          }}
          disabled={readOnly}
        />
      </div>
    )
  }

  if (!schema || Object.keys(schema).length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-4">
        此策略无需额外参数
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {Object.entries(schema).map(([key, paramConfig]) =>
        renderField(key, paramConfig)
      )}
    </div>
  )
})

StrategyConfigEditor.displayName = 'StrategyConfigEditor'

export default StrategyConfigEditor
