'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Edit, AlertCircle, Copy, Check } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'

// 策略类型显示名称
const strategyTypeNames = {
  stock_selection: '选股策略',
  entry: '入场策略',
  exit: '离场策略',
}

// 策略类别显示名称
const categoryNames: Record<string, string> = {
  momentum: '动量策略',
  reversal: '反转策略',
  mean_reversion: '均值回归策略',
  factor: '因子策略',
  ml: '机器学习策略',
  arbitrage: '套利策略',
  hybrid: '混合策略',
  trend_following: '趋势跟踪策略',
  breakout: '突破策略',
  statistical: '统计套利策略',
}

export default function StrategyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const strategyId = params.id as string

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedHash, setCopiedHash] = useState(false)

  const handleCopyHash = async () => {
    if (strategy?.code_hash) {
      await navigator.clipboard.writeText(strategy.code_hash)
      setCopiedHash(true)
      setTimeout(() => setCopiedHash(false), 2000)
    }
  }

  useEffect(() => {
    const fetchStrategy = async () => {
      try {
        const result = await apiClient.getStrategy(Number(strategyId))
        if (result.success || result.data) {
          setStrategy(result.data || result as any)
        } else {
          throw new Error((result as any).message || '获取策略详情失败')
        }
      } catch (err: any) {
        logger.error('获取策略详情失败', err)
        setError(err.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchStrategy()
  }, [strategyId])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className="p-4 sm:p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error || '策略不存在'}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6">
      {/* 页面头部 */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {strategy.display_name}
          </h1>
          <p className="mt-1 text-sm text-gray-600">{strategy.name}</p>
        </div>
        {strategy.source_type !== 'builtin' && (
          <button
            onClick={() => router.push(`/strategies/${strategyId}/edit`)}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 w-full sm:w-auto"
          >
            <Edit className="h-4 w-4" />
            编辑
          </button>
        )}
      </div>

      {/* 基本信息 */}
      <div className="mb-6 grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">基本信息</h3>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-600">策略类型</div>
              <div className="mt-1 font-medium">
                {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">用户</div>
              <div className="mt-1 font-medium">
                {strategy.username || <span className="text-gray-500 italic">系统策略</span>}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">类名</div>
              <div className="mt-1 flex items-center gap-2">
                <div
                  className="font-mono text-sm text-gray-700 truncate cursor-default"
                  title={strategy.class_name}
                >
                  {strategy.class_name}
                </div>
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(strategy.class_name)
                    const btn = document.activeElement as HTMLElement
                    const originalText = btn.textContent
                    btn.textContent = '✓'
                    setTimeout(() => {
                      btn.textContent = originalText || ''
                    }, 2000)
                  }}
                  className="flex-shrink-0 text-xs text-gray-500 hover:text-gray-700 px-1"
                  title="复制类名"
                >
                  复制
                </button>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">类别</div>
              <div className="mt-1">
                {strategy.category ? (categoryNames[strategy.category] || strategy.category) : '-'}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">验证状态</h3>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-600">验证状态</div>
              <div className="mt-1">
                <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                  strategy.validation_status === 'passed' ? 'bg-green-100 text-green-800' :
                  strategy.validation_status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {strategy.validation_status}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">风险等级</div>
              <div className="mt-1">
                <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                  strategy.risk_level === 'safe' ? 'bg-green-100 text-green-800' :
                  strategy.risk_level === 'low' ? 'bg-blue-100 text-blue-800' :
                  strategy.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {strategy.risk_level}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">启用状态</div>
              <div className="mt-1">
                <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                  strategy.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {strategy.is_enabled ? '已启用' : '已禁用'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">使用统计</h3>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-600">使用次数</div>
              <div className="mt-1 text-2xl font-bold">{strategy.usage_count}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">回测次数</div>
              <div className="mt-1 text-2xl font-bold">{strategy.backtest_count}</div>
            </div>
            {strategy.avg_sharpe_ratio && (
              <div>
                <div className="text-sm text-gray-600">平均夏普率</div>
                <div className="mt-1 text-2xl font-bold">
                  {Number(strategy.avg_sharpe_ratio).toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 描述 */}
      {strategy.description && (
        <div className="mb-4 sm:mb-6 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">描述</h3>
          <p className="text-sm sm:text-base text-gray-700">{strategy.description}</p>
        </div>
      )}

      {/* 标签 */}
      {strategy.tags && strategy.tags.length > 0 && (
        <div className="mb-4 sm:mb-6 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">标签</h3>
          <div className="flex flex-wrap gap-2">
            {strategy.tags.map((tag, index) => (
              <span
                key={index}
                className="rounded-full bg-blue-100 px-3 py-1 text-xs sm:text-sm text-blue-800"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 默认参数 */}
      {strategy.default_params && Object.keys(strategy.default_params).length > 0 && (
        <div className="mb-4 sm:mb-6 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold">默认参数</h3>
          <pre className="overflow-x-auto rounded bg-gray-50 p-3 sm:p-4 text-xs sm:text-sm">
            {JSON.stringify(strategy.default_params, null, 2)}
          </pre>
        </div>
      )}

      {/* 策略代码 */}
      <div className="mb-4 sm:mb-6 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
        <h3 className="mb-4 text-base sm:text-lg font-semibold">策略代码</h3>
        <pre className="overflow-x-auto rounded bg-gray-900 p-3 sm:p-4 text-xs sm:text-sm text-green-400">
          <code>{strategy.code}</code>
        </pre>
      </div>

      {/* 验证错误和警告 */}
      {strategy.validation_errors && Object.keys(strategy.validation_errors).length > 0 && (
        <div className="mb-4 sm:mb-6 rounded-lg border border-red-200 bg-red-50 p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold text-red-800">验证错误</h3>
          <pre className="overflow-x-auto rounded bg-white p-3 sm:p-4 text-xs sm:text-sm text-red-600">
            {JSON.stringify(strategy.validation_errors, null, 2)}
          </pre>
        </div>
      )}

      {strategy.validation_warnings && Object.keys(strategy.validation_warnings).length > 0 && (
        <div className="mb-4 sm:mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 sm:p-6">
          <h3 className="mb-4 text-base sm:text-lg font-semibold text-yellow-800">验证警告</h3>
          <pre className="overflow-x-auto rounded bg-white p-3 sm:p-4 text-xs sm:text-sm text-yellow-600">
            {JSON.stringify(strategy.validation_warnings, null, 2)}
          </pre>
        </div>
      )}

      {/* 元数据 */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
        <h3 className="mb-4 text-base sm:text-lg font-semibold">元数据</h3>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          <div>
            <div className="text-sm text-gray-600">创建时间</div>
            <div className="mt-1">{new Date(strategy.created_at).toLocaleString('zh-CN')}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">更新时间</div>
            <div className="mt-1">{new Date(strategy.updated_at).toLocaleString('zh-CN')}</div>
          </div>
          {strategy.created_by && (
            <div>
              <div className="text-sm text-gray-600">创建人</div>
              <div className="mt-1">{strategy.created_by}</div>
            </div>
          )}
          <div>
            <div className="text-sm text-gray-600">版本</div>
            <div className="mt-1">v{strategy.version}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">代码哈希</div>
            <div className="mt-1 flex items-center gap-2">
              <div
                className="font-mono text-xs text-gray-700 truncate max-w-[200px] cursor-default"
                title={strategy.code_hash}
              >
                {strategy.code_hash}
              </div>
              <button
                onClick={handleCopyHash}
                className="flex-shrink-0 p-1 rounded hover:bg-gray-100 transition-colors"
                title="复制完整哈希"
              >
                {copiedHash ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-500" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
