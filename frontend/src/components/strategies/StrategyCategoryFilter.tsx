/**
 * 策略类别筛选组件
 * 用于统一管理策略中心、我的策略等页面的类别筛选下拉框
 */

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { STRATEGY_CATEGORIES } from '@/types/strategy'

interface StrategyCategoryFilterProps {
  value: string
  onValueChange: (value: string) => void
  placeholder?: string
  showAllOption?: boolean
  allOptionLabel?: string
}

export default function StrategyCategoryFilter({
  value,
  onValueChange,
  placeholder = '选择类别',
  showAllOption = true,
  allOptionLabel = '全部类别'
}: StrategyCategoryFilterProps) {
  return (
    <Select value={value} onValueChange={onValueChange}>
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {showAllOption && (
          <SelectItem value="all">{allOptionLabel}</SelectItem>
        )}
        {STRATEGY_CATEGORIES.map((cat) => (
          <SelectItem key={cat.value} value={cat.value}>
            <div className="flex flex-col">
              <span>{cat.label}</span>
              <span className="text-xs text-muted-foreground">{cat.description}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
