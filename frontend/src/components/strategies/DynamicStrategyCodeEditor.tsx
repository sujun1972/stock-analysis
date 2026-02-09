/**
 * 动态策略代码编辑器组件
 * 提供代码编辑界面（使用 textarea，未来可升级为 Monaco Editor）
 */

'use client'

import { memo } from 'react'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface DynamicStrategyCodeEditorProps {
  value: string
  onChange: (code: string) => void
  readOnly?: boolean
  minHeight?: string
}

const DynamicStrategyCodeEditor = memo(function DynamicStrategyCodeEditor({
  value,
  onChange,
  readOnly = false,
  minHeight = '400px'
}: DynamicStrategyCodeEditorProps) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">策略代码 (Python)</Label>
      <div className="border rounded-lg overflow-hidden">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          readOnly={readOnly}
          className="font-mono text-sm resize-none border-0 focus-visible:ring-0"
          style={{ minHeight }}
          placeholder={`from core.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    """
    自定义策略示例
    """

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        """
        生成交易信号

        参数:
            prices: 价格数据 (DataFrame)
            features: 特征数据 (DataFrame, 可选)
            volumes: 成交量数据 (DataFrame, 可选)

        返回:
            signals: 交易信号 (DataFrame)
        """
        # TODO: 实现你的策略逻辑
        pass
`}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        提示: 策略类必须继承 BaseStrategy 并实现 generate_signals 方法
      </p>
    </div>
  )
})

DynamicStrategyCodeEditor.displayName = 'DynamicStrategyCodeEditor'

export default DynamicStrategyCodeEditor
