'use client'

import type { ParameterDef } from '@/lib/three-layer-types'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'

interface ParametersFormProps {
  parameters: ParameterDef[]
  values: Record<string, any>
  onChange: (values: Record<string, any>) => void
}

export function ParametersForm({ parameters, values, onChange }: ParametersFormProps) {
  const handleChange = (name: string, value: any) => {
    onChange({ ...values, [name]: value })
  }

  const getValue = (param: ParameterDef) => {
    return values[param.name] ?? param.default
  }

  if (parameters.length === 0) {
    return (
      <p className="text-sm text-muted-foreground mt-4">
        该策略无需配置参数
      </p>
    )
  }

  return (
    <div className="space-y-4 mt-4">
      {parameters.map(param => (
        <div key={param.name} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <div className="md:col-span-1">
            <Label htmlFor={param.name} className="text-sm font-medium">
              {param.label}
            </Label>
            {param.description && (
              <p className="text-xs text-muted-foreground mt-1">
                {param.description}
              </p>
            )}
          </div>

          <div className="md:col-span-2">
            {param.type === 'integer' || param.type === 'float' ? (
              <div className="space-y-2">
                <div className="flex gap-2 items-center">
                  <Slider
                    id={param.name}
                    min={param.min_value}
                    max={param.max_value}
                    step={param.step || (param.type === 'integer' ? 1 : 0.1)}
                    value={[getValue(param)]}
                    onValueChange={([v]) => handleChange(param.name, v)}
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    min={param.min_value}
                    max={param.max_value}
                    step={param.step || (param.type === 'integer' ? 1 : 0.1)}
                    value={getValue(param)}
                    onChange={(e) => {
                      const val = e.target.value
                      const numVal = param.type === 'integer'
                        ? parseInt(val)
                        : parseFloat(val)
                      if (!isNaN(numVal)) {
                        handleChange(param.name, numVal)
                      }
                    }}
                    className="w-24"
                  />
                </div>
                {(param.min_value !== undefined || param.max_value !== undefined) && (
                  <p className="text-xs text-muted-foreground">
                    范围: {param.min_value ?? '-∞'} ~ {param.max_value ?? '∞'}
                  </p>
                )}
              </div>
            ) : param.type === 'boolean' ? (
              <div className="flex items-center space-x-2">
                <Switch
                  id={param.name}
                  checked={getValue(param)}
                  onCheckedChange={(checked) => handleChange(param.name, checked)}
                />
                <Label htmlFor={param.name} className="text-sm text-muted-foreground">
                  {getValue(param) ? '启用' : '禁用'}
                </Label>
              </div>
            ) : param.type === 'select' ? (
              <Select
                value={String(getValue(param))}
                onValueChange={(value) => handleChange(param.name, value)}
              >
                <SelectTrigger id={param.name}>
                  <SelectValue placeholder="请选择..." />
                </SelectTrigger>
                <SelectContent>
                  {param.options?.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Input
                id={param.name}
                type="text"
                value={getValue(param)}
                onChange={(e) => handleChange(param.name, e.target.value)}
                placeholder={`请输入${param.label}`}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
