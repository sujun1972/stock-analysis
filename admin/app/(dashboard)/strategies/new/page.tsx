'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { AlertCircle, CheckCircle, Loader, Save } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/common/PageHeader'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'

// 动态导入 Monaco Editor (客户端组件)
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[400px] items-center justify-center rounded-lg border bg-gray-50">
      <Loader className="h-8 w-8 animate-spin text-blue-600" />
    </div>
  ),
})

// 检测是否为移动设备
const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  return isMobile
}

export default function NewStrategyPage() {
  const router = useRouter()
  const isMobile = useIsMobile()
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    class_name: '',
    code: '',
    source_type: 'custom',
    strategy_type: 'stock_selection',
    description: '',
    category: '',
    tags: '',
    default_params: '{}',
    user_id: '',
  })

  // 验证策略代码
  const handleValidate = async () => {
    setValidating(true)
    setValidationResult(null)
    setError(null)

    try {
      const result = await apiClient.validateStrategy(formData.code)
      if (result.success || result.data) {
        setValidationResult(result.data || result)
      } else {
        setError((result as any).message || '验证失败')
      }
    } catch (err: any) {
      logger.error('验证策略代码失败', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setValidating(false)
    }
  }

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // 解析JSON字段
      let defaultParams = null
      if (formData.default_params.trim()) {
        try {
          defaultParams = JSON.parse(formData.default_params)
        } catch {
          throw new Error('默认参数格式错误，请输入有效的JSON')
        }
      }

      // 解析标签
      const tags = formData.tags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t)

      const payload: any = {
        name: formData.name,
        display_name: formData.display_name,
        class_name: formData.class_name,
        code: formData.code,
        source_type: formData.source_type as any,
        strategy_type: formData.strategy_type as any,
        description: formData.description || undefined,
        category: formData.category || undefined,
        tags: tags.length > 0 ? tags : undefined,
        default_params: defaultParams,
        created_by: 'admin',
      }

      // 如果指定了user_id，添加到payload
      if (formData.user_id) {
        payload.user_id = parseInt(formData.user_id)
      }

      const result = await apiClient.createStrategy(payload)

      if (result.success || result.data) {
        const strategyId = result.data?.strategy_id || (result as any).strategy_id
        // 成功跳转到策略详情页
        router.push(`/strategies/${strategyId}`)
      } else {
        throw new Error((result as any).message || '创建失败')
      }
    } catch (err: any) {
      logger.error('创建策略失败', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 sm:p-6">
      {/* 页面头部 */}
      <PageHeader
        title="创建新策略"
        description="填写策略信息并验证代码"
      />

      {/* 错误提示 */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* 验证结果 */}
      {validationResult && (
        <div
          className={`mb-6 rounded-lg border p-4 ${
            validationResult.is_valid
              ? 'border-green-200 bg-green-50'
              : 'border-red-200 bg-red-50'
          }`}
        >
          <div className="flex items-center gap-2">
            {validationResult.is_valid ? (
              <>
                <CheckCircle className="h-5 w-5 text-green-600" />
                <p className="text-green-800">代码验证通过</p>
              </>
            ) : (
              <>
                <AlertCircle className="h-5 w-5 text-red-600" />
                <p className="text-red-800">代码验证失败</p>
              </>
            )}
          </div>
          {validationResult.errors && validationResult.errors.length > 0 && (
            <div className="mt-2">
              <div className="text-sm font-semibold text-red-800">错误:</div>
              <ul className="ml-4 list-disc text-sm text-red-700">
                {validationResult.errors.map((err: string, i: number) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}
          {validationResult.warnings && validationResult.warnings.length > 0 && (
            <div className="mt-2">
              <div className="text-sm font-semibold text-yellow-800">警告:</div>
              <ul className="ml-4 list-disc text-sm text-yellow-700">
                {validationResult.warnings.map((warn: string, i: number) => (
                  <li key={i}>{warn}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="mt-2 text-sm">
            <span className="font-semibold">风险等级:</span>{' '}
            <span
              className={`ml-2 rounded-full px-2 py-1 text-xs font-semibold ${
                validationResult.risk_level === 'safe'
                  ? 'bg-green-100 text-green-800'
                  : validationResult.risk_level === 'low'
                  ? 'bg-blue-100 text-blue-800'
                  : validationResult.risk_level === 'medium'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {validationResult.risk_level}
            </span>
          </div>
        </div>
      )}

      {/* 表单 */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
          {/* 基本信息 */}
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
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
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
                onChange={(e) =>
                  setFormData({ ...formData, class_name: e.target.value })
                }
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
                onValueChange={(value) =>
                  setFormData({ ...formData, strategy_type: value })
                }
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
                onValueChange={(value) =>
                  setFormData({ ...formData, source_type: value })
                }
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
                onChange={(e) =>
                  setFormData({ ...formData, user_id: e.target.value })
                }
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="留空表示系统策略"
              />
            </div>
          </div>

          {/* 元信息 */}
          <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
            <h3 className="text-lg font-semibold">元信息</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                描述
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
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
                onChange={(e) =>
                  setFormData({ ...formData, category: e.target.value })
                }
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
                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
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
                onChange={(e) =>
                  setFormData({ ...formData, default_params: e.target.value })
                }
                rows={4}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder='{"lookback_period": 20, "top_n": 50}'
              />
            </div>
          </div>
        </div>

        {/* 策略代码 */}
        <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-lg font-semibold">
            策略代码 <span className="text-red-500">*</span>
          </h3>
          <div className="overflow-hidden rounded-lg border border-gray-300">
            {isMobile ? (
              <textarea
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full h-[400px] bg-gray-900 text-green-400 font-mono text-sm p-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="# 示例:选股策略&#10;class MyStockSelectionStrategy:&#10;    &quot;&quot;&quot;&#10;    自定义选股策略&#10;    &quot;&quot;&quot;&#10;    def select_stocks(self, universe, features, date):&#10;        &quot;&quot;&quot;选择股票&quot;&quot;&quot;&#10;        # TODO: 实现你的选股逻辑&#10;        pass"
              />
            ) : (
              <Editor
                height="400px"
                defaultLanguage="python"
                value={formData.code}
                onChange={(value) => setFormData({ ...formData, code: value || '' })}
                theme="vs-dark"
                loading={<div className="flex h-[400px] items-center justify-center"><Loader className="h-8 w-8 animate-spin text-blue-600" /></div>}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 4,
                  wordWrap: 'on',
                  formatOnPaste: false,
                  formatOnType: false,
                  quickSuggestions: false,
                  suggestOnTriggerCharacters: false,
                  acceptSuggestionOnCommitCharacter: false,
                  acceptSuggestionOnEnter: 'off',
                  snippetSuggestions: 'none',
                }}
                defaultValue={`# 示例:选股策略
class MyStockSelectionStrategy:
    """
    自定义选股策略
    """
    def select_stocks(self, universe, features, date):
        """
        选择股票

        Args:
            universe: 股票池列表
            features: 特征数据
            date: 当前日期

        Returns:
            list: 选中的股票代码列表
        """
        # TODO: 实现你的选股逻辑
        pass
`}
              />
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={handleValidate}
              disabled={validating || !formData.code}
              className="flex items-center justify-center gap-2 rounded-lg border border-blue-600 px-4 py-2 text-sm sm:text-base text-blue-600 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50 w-full sm:w-auto"
            >
              {validating && <Loader className="h-4 w-4 animate-spin" />}
              验证代码
            </button>
          </div>
        </div>

        {/* 提交按钮 */}
        <div className="flex flex-row gap-2 sm:gap-3">
          <button
            type="submit"
            disabled={loading}
            className="flex flex-1 sm:flex-initial items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 sm:px-6 py-2.5 text-sm sm:text-base text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            创建策略
          </button>
          <button
            type="button"
            onClick={() => router.push('/strategies')}
            className="flex-1 sm:flex-initial rounded-lg border border-gray-300 px-4 sm:px-6 py-2.5 text-sm sm:text-base text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  )
}
