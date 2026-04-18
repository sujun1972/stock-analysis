'use client'

import type { NewStrategyFormData } from '../hooks/useNewStrategyForm'

interface MetaInfoSectionProps {
  formData: NewStrategyFormData
  updateField: <K extends keyof NewStrategyFormData>(field: K, value: NewStrategyFormData[K]) => void
}

export function MetaInfoSection({ formData, updateField }: MetaInfoSectionProps) {
  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
      <h3 className="text-lg font-semibold">元信息</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          描述
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => updateField('description', e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="策略的详细描述..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          类别
        </label>
        <input
          type="text"
          value={formData.category}
          onChange={(e) => updateField('category', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="momentum, reversal, factor等"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          标签
        </label>
        <input
          type="text"
          value={formData.tags}
          onChange={(e) => updateField('tags', e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="动量, 趋势, 短期 (逗号分隔)"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          默认参数 (JSON格式)
        </label>
        <textarea
          value={formData.default_params}
          onChange={(e) => updateField('default_params', e.target.value)}
          rows={4}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder='{"lookback_period": 20, "top_n": 50}'
        />
      </div>
    </div>
  )
}
