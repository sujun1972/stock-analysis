'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'

export default function SettingsPage() {
  const [dataSource, setDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [tushareToken, setTushareToken] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await apiClient.getDataSourceConfig()

      if (response.data) {
        setDataSource(response.data.data_source as 'akshare' | 'tushare')
        setTushareToken(response.data.tushare_token || '')
      }
    } catch (err: any) {
      setError(err.message || '加载配置失败')
      console.error('Failed to load config:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setIsSaving(true)
      setError(null)
      setSuccessMessage(null)

      // 验证：如果选择 Tushare，必须提供 Token
      if (dataSource === 'tushare' && !tushareToken.trim()) {
        setError('使用 Tushare 数据源需要提供 API Token')
        return
      }

      await apiClient.updateDataSourceConfig({
        data_source: dataSource,
        tushare_token: tushareToken.trim()
      })

      setSuccessMessage(`成功切换数据源为 ${dataSource === 'akshare' ? 'AkShare' : 'Tushare'}`)

      // 5秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      setError(err.message || '保存配置失败')
      console.error('Failed to save config:', err)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          系统设置
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          配置数据源和系统参数
        </p>
      </div>

      {/* 成功消息 */}
      {successMessage && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-600 dark:text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-green-800 dark:text-green-200">{successMessage}</span>
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-800 dark:text-red-200">{error}</span>
          </div>
        </div>
      )}

      {/* 数据源配置 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          数据源配置
        </h2>

        {isLoading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 数据源选择 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                选择数据源
              </label>

              <div className="space-y-3">
                {/* AkShare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  dataSource === 'akshare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <input
                    type="radio"
                    name="dataSource"
                    value="akshare"
                    checked={dataSource === 'akshare'}
                    onChange={(e) => setDataSource(e.target.value as 'akshare')}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">AkShare</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                        免费
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      免费开源的 Python 金融数据接口，无需 Token，支持 A 股、港股、美股等多种数据
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>✓ 无需注册和积分</p>
                      <p>✓ 数据来源稳定（东方财富、新浪财经等）</p>
                      <p>⚠ 存在 IP 限流风险，建议请求间隔 &ge; 0.3秒</p>
                    </div>
                  </div>
                </label>

                {/* Tushare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  dataSource === 'tushare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <input
                    type="radio"
                    name="dataSource"
                    value="tushare"
                    checked={dataSource === 'tushare'}
                    onChange={(e) => setDataSource(e.target.value as 'tushare')}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">Tushare Pro</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                        需要积分
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      专业的金融数据接口，需要注册获取 Token，数据质量高、覆盖全面
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>✓ 数据质量高，覆盖全面</p>
                      <p>⚠ 需要积分：日线数据 120 分、分钟数据 2000 分、实时行情 5000 分</p>
                      <p>⚠ 有频率限制（与积分等级相关）</p>
                    </div>
                  </div>
                </label>
              </div>
            </div>

            {/* Tushare Token 输入 */}
            {dataSource === 'tushare' && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tushare API Token *
                </label>
                <input
                  type="text"
                  value={tushareToken}
                  onChange={(e) => setTushareToken(e.target.value)}
                  placeholder="请输入您的 Tushare Token"
                  className="input-field"
                />
                <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                  没有 Token？
                  <a
                    href="https://tushare.pro/register?reg=430522"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline ml-1"
                  >
                    点击注册 Tushare 账号
                  </a>
                </p>
              </div>
            )}

            {/* 保存按钮 */}
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn-primary"
              >
                {isSaving ? '保存中...' : '保存配置'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 数据源对比说明 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          数据源对比
        </h2>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  特性
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  AkShare
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Tushare Pro
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  使用成本
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  <span className="text-green-600 dark:text-green-400 font-medium">免费</span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  需要积分（注册送 120 分）
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  日线数据
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持 (120积分)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  分钟数据
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持 (2000积分)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  实时行情
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持 (较慢)
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ 支持 (5000积分)
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  数据质量
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  较好
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  <span className="text-blue-600 dark:text-blue-400 font-medium">优秀</span>
                </td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                  频率限制
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  IP 限流风险
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                  按积分等级限制
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
