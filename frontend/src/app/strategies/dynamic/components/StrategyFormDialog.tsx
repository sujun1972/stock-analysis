'use client'

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import DynamicStrategyCodeEditor from '@/components/strategies/DynamicStrategyCodeEditor'
import StrategyValidationResult from '@/components/strategies/StrategyValidationResult'
import { Loader2 } from 'lucide-react'
import type { StrategyFormData, ValidationResult } from '../hooks/useDynamicStrategies'

interface StrategyFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  formData: StrategyFormData
  onFormDataChange: (data: StrategyFormData) => void
  validationResult: ValidationResult | null
  isLoading: boolean
  onValidateCode: () => void
  onSubmit: () => void
}

export default function StrategyFormDialog({
  mode,
  open,
  onOpenChange,
  formData,
  onFormDataChange,
  validationResult,
  isLoading,
  onValidateCode,
  onSubmit,
}: StrategyFormDialogProps) {
  const isCreate = mode === 'create'
  const title = isCreate ? '新建动态策略' : '编辑动态策略'
  const description = isCreate
    ? '编写自定义策略代码，实现个性化的交易逻辑'
    : '修改策略代码和配置信息'
  const submitLabel = isCreate ? '创建策略' : '保存更改'

  const updateField = <K extends keyof StrategyFormData>(field: K, value: StrategyFormData[K]) => {
    onFormDataChange({ ...formData, [field]: value })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {isCreate ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="create-strategy-name">策略名称 * (英文, 用于文件名)</Label>
                  <Input
                    id="create-strategy-name"
                    placeholder="my_custom_strategy"
                    value={formData.strategy_name}
                    onChange={(e) => updateField('strategy_name', e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    小写字母、数字和下划线，如: my_momentum_strategy
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="create-display-name">显示名称 *</Label>
                  <Input
                    id="create-display-name"
                    placeholder="我的自定义策略"
                    value={formData.display_name}
                    onChange={(e) => updateField('display_name', e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="create-class-name">类名 * (Python 类名)</Label>
                <Input
                  id="create-class-name"
                  placeholder="MyCustomStrategy"
                  value={formData.class_name}
                  onChange={(e) => updateField('class_name', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  大写驼峰命名，如: MyMomentumStrategy
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label>策略名称</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{formData.strategy_name}</Badge>
                  <span className="text-sm text-muted-foreground">
                    (策略名称不可修改)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-display-name">显示名称 *</Label>
                  <Input
                    id="edit-display-name"
                    value={formData.display_name}
                    onChange={(e) => updateField('display_name', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>类名</Label>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{formData.class_name}</Badge>
                    <span className="text-sm text-muted-foreground">
                      (类名不可修改)
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor={`${mode}-description`}>描述</Label>
            <Textarea
              id={`${mode}-description`}
              placeholder="简要描述此策略的逻辑和用途..."
              value={formData.description}
              onChange={(e) => updateField('description', e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">策略代码 *</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onValidateCode}
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                验证代码
              </Button>
            </div>
            <DynamicStrategyCodeEditor
              value={formData.generated_code}
              onChange={(code) => updateField('generated_code', code)}
              minHeight="400px"
            />
          </div>

          {validationResult && (
            <StrategyValidationResult
              isValid={validationResult.is_valid}
              errors={validationResult.errors.map(e => ({ type: 'error', message: e }))}
              warnings={validationResult.warnings.map(w => ({ type: 'warning', message: w }))}
            />
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            取消
          </Button>
          <Button onClick={onSubmit} disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
