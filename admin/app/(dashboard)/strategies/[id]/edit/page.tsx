'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { AlertCircle, CheckCircle, Loader, Save } from 'lucide-react'
import { Switch } from '@/components/ui/switch'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

export default function EditStrategyPage() {
  const params = useParams()
  const router = useRouter()
  const strategyId = params.id as string
  const isMobile = useIsMobile()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    display_name: '',
    description: '',
    code: '',
    tags: '',
    default_params: '{}',
    is_enabled: true,
  })

  const [originalStrategy, setOriginalStrategy] = useState<any>(null)

  // 加载策略数据
  useEffect(() => {
    const fetchStrategy = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/strategies/${strategyId}`)
        if (!response.ok) {
          throw new Error('获取策略详情失败')
        }

        const result = await response.json()
        if (result.success) {
          const strategy = result.data
          setOriginalStrategy(strategy)
          setFormData({
            display_name: strategy.display_name,
            description: strategy.description || '',
            code: strategy.code,
            tags: strategy.tags?.join(', ') || '',
            default_params: strategy.default_params
              ? JSON.stringify(strategy.default_params, null, 2)
              : '{}',
            is_enabled: strategy.is_enabled,
          })
        } else {
          throw new Error(result.message || '获取策略详情失败')
        }
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchStrategy()
  }, [strategyId])

  // 验证策略代码
  const handleValidate = async () => {
    setValidating(true)
    setValidationResult(null)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/strategies/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: formData.code,
          strict_mode: true,
        }),
      })

      const result = await response.json()
      if (result.success) {
        setValidationResult(result.data)
      } else {
        setError(result.message || '验证失败')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setValidating(false)
    }
  }

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
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
        display_name: formData.display_name,
        description: formData.description || undefined,
        is_enabled: formData.is_enabled,
      }

      // 只有当代码被修改时才发送
      if (formData.code !== originalStrategy?.code) {
        payload.code = formData.code
      }

      // 只有当标签被修改时才发送
      const originalTags = originalStrategy?.tags?.join(', ') || ''
      if (formData.tags !== originalTags) {
        payload.tags = tags.length > 0 ? tags : undefined
      }

      // 只有当参数被修改时才发送
      const originalParams = originalStrategy?.default_params
        ? JSON.stringify(originalStrategy.default_params, null, 2)
        : '{}'
      if (formData.default_params !== originalParams) {
        payload.default_params = defaultParams
      }

      const response = await fetch(`${API_BASE_URL}/api/strategies/${strategyId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const result = await response.json()
      if (result.success) {
        // 成功跳转到策略详情页
        router.push(`/strategies/${strategyId}`)
      } else {
        throw new Error(result.message || '更新失败')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (error && !originalStrategy) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6">
      {/* 页面头部 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">编辑策略</h1>
        <p className="mt-1 text-sm text-gray-600">{originalStrategy?.name}</p>
      </div>

      {/* 系统策略提示 */}
      {originalStrategy?.source_type === 'builtin' && (
        <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <p className="text-yellow-800">
              系统内置策略不允许修改代码，只能修改描述、标签等元信息
            </p>
          </div>
        </div>
      )}

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
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                描述
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={4}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="策略的详细描述..."
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
              <label className="flex items-center gap-3">
                <Switch
                  checked={formData.is_enabled}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_enabled: checked })
                  }
                />
                <span className="text-sm font-medium text-gray-700">
                  {formData.is_enabled ? '策略已启用' : '策略已禁用'}
                </span>
              </label>
              <p className="mt-1 text-xs text-gray-500">
                禁用后，该策略将不会在前端策略中心显示，但已有的回测记录不受影响
              </p>
            </div>
          </div>

          {/* 参数配置 */}
          <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
            <h3 className="text-lg font-semibold">参数配置</h3>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                默认参数 (JSON格式)
              </label>
              <textarea
                value={formData.default_params}
                onChange={(e) =>
                  setFormData({ ...formData, default_params: e.target.value })
                }
                rows={10}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder='{"lookback_period": 20, "top_n": 50}'
              />
              <p className="mt-1 text-xs text-gray-500">
                修改策略的默认参数配置
              </p>
            </div>
          </div>
        </div>

        {/* 策略代码 */}
        <div className="rounded-lg border border-gray-200 bg-white p-4 sm:p-6">
          <h3 className="mb-4 text-lg font-semibold">
            策略代码 {originalStrategy?.source_type === 'builtin' && '(只读)'}
          </h3>
          <div className="overflow-hidden rounded-lg border border-gray-300">
            {isMobile ? (
              <textarea
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                readOnly={originalStrategy?.source_type === 'builtin'}
                className="w-full h-[400px] bg-gray-900 text-green-400 font-mono text-sm p-4 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                disabled={originalStrategy?.source_type === 'builtin'}
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
                  readOnly: originalStrategy?.source_type === 'builtin',
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
              />
            )}
          </div>
          {originalStrategy?.source_type !== 'builtin' && (
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
          )}
        </div>

        {/* 提交按钮 */}
        <div className="flex flex-row gap-2 sm:gap-3">
          <button
            type="submit"
            disabled={saving}
            className="flex flex-1 sm:flex-initial items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 sm:px-6 py-2.5 text-sm sm:text-base text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            保存修改
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
