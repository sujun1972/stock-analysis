'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { NewStrategyFormData } from '../hooks/useNewStrategyForm'

interface BasicInfoSectionProps {
  formData: NewStrategyFormData
  updateField: <K extends keyof NewStrategyFormData>(field: K, value: NewStrategyFormData[K]) => void
}

export function BasicInfoSection({ formData, updateField }: BasicInfoSectionProps) {
  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
      <h3 className="text-lg font-semibold">基本信息</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          策略名称 <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          required
          value={formData.name}
          onChange={(e) => updateField('name', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="momentum_20d"
        />
        <p className="mt-1 text-xs text-gray-500">
          唯一标识，使用小写字母、数字和下划线
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          显示名称 <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          required
          value={formData.display_name}
          onChange={(e) => updateField('display_name', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="动量策略 20日"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          类名 <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          required
          value={formData.class_name}
          onChange={(e) => updateField('class_name', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="MomentumStrategy"
        />
        <p className="mt-1 text-xs text-gray-500">
          Python类名，首字母大写
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          策略类型 <span className="text-red-500">*</span>
        </label>
        <Select
          required
          value={formData.strategy_type}
          onValueChange={(value) => updateField('strategy_type', value)}
        >
          <SelectTrigger className="mt-1 w-full">
            <SelectValue placeholder="选择策略类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="stock_selection">选股策略</SelectItem>
            <SelectItem value="entry">入场策略</SelectItem>
            <SelectItem value="exit">离场策略</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          来源类型
        </label>
        <Select
          value={formData.source_type}
          onValueChange={(value) => updateField('source_type', value)}
        >
          <SelectTrigger className="mt-1 w-full">
            <SelectValue placeholder="选择来源类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="custom">用户自定义</SelectItem>
            <SelectItem value="ai">AI生成</SelectItem>
            <SelectItem value="builtin">系统内置</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          用户ID (可选)
        </label>
        <input
          type="number"
          value={formData.user_id}
          onChange={(e) => updateField('user_id', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="留空表示系统策略"
        />
      </div>
    </div>
  )
}
