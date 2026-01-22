'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'

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
          <div key={param.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {param.label}
              </label>
              <input
                type="number"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseInt(e.target.value) || param.default)}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 1}
                className="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
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
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            )}
            <p className="text-xs text-gray-500 dark:text-gray-400">{param.description}</p>
          </div>
        )

      case 'float':
        return (
          <div key={param.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {param.label}
              </label>
              <input
                type="number"
                value={value}
                onChange={(e) => handleParamChange(param.name, parseFloat(e.target.value) || param.default)}
                min={param.min_value}
                max={param.max_value}
                step={param.step || 0.1}
                className="w-24 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
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
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            )}
            <p className="text-xs text-gray-500 dark:text-gray-400">{param.description}</p>
          </div>
        )

      case 'boolean':
        return (
          <div key={param.name} className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {param.label}
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400">{param.description}</p>
            </div>
            <button
              onClick={() => handleParamChange(param.name, !value)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                value ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  value ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        )

      case 'select':
        return (
          <div key={param.name} className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {param.label}
            </label>
            <select
              value={value}
              onChange={(e) => handleParamChange(param.name, e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {param.options?.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400">{param.description}</p>
          </div>
        )

      default:
        return null
    }
  }

  if (loading) {
    return (
      <div className={isInDialog ? "p-6" : "bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-400">加载策略参数...</span>
        </div>
      </div>
    )
  }

  if (!metadata) {
    return (
      <div className={isInDialog ? "p-6" : "bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"}>
        <p className="text-red-600 dark:text-red-400">无法加载策略参数</p>
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
          <button
            onClick={handleReset}
            className="text-xs sm:text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            重置为默认值
          </button>
        </div>

        {/* 参数配置区域 - 两列布局（大屏幕） */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
          {Object.entries(paramsByCategory).map(([category, categoryParams]) => (
            <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 sm:p-4 space-y-3 sm:space-y-4">
              <h4 className="font-semibold text-sm sm:text-base text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
                {category}
              </h4>
              <div className="space-y-3 sm:space-y-4">
                {categoryParams.map(param => renderParamInput(param))}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // 原有的完整布局（用于非对话框场景）
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
      {/* 策略信息头部 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
          {metadata.name}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {metadata.description}
        </p>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            版本 {metadata.version}
          </span>
          <button
            onClick={handleReset}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            重置为默认值
          </button>
        </div>
      </div>

      {/* 参数配置区域 */}
      <div className="p-4 space-y-4 max-h-[600px] overflow-y-auto">
        {Object.entries(paramsByCategory).map(([category, categoryParams]) => (
          <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg">
            <button
              onClick={() => toggleCategory(category)}
              className="w-full px-4 py-2 flex items-center justify-between bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors rounded-t-lg"
            >
              <span className="font-medium text-gray-900 dark:text-white">{category}</span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${
                  expandedCategories.has(category) ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {expandedCategories.has(category) && (
              <div className="p-4 space-y-4">
                {categoryParams.map(param => renderParamInput(param))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 底部操作按钮 */}
      {onApply && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onApply}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            应用参数并回测
          </button>
        </div>
      )}
    </div>
  )
}
