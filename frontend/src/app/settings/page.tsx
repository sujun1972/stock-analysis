'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

export default function SettingsPage() {
  const [dataSource, setDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [realtimeDataSource, setRealtimeDataSource] = useState<'akshare' | 'tushare'>('akshare')
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
        setRealtimeDataSource(response.data.realtime_data_source as 'akshare' | 'tushare')
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

      // 验证：如果任一数据源选择 Tushare，必须提供 Token
      if ((dataSource === 'tushare' || realtimeDataSource === 'tushare') && !tushareToken.trim()) {
        setError('使用 Tushare 数据源需要提供 API Token')
        return
      }

      await apiClient.updateDataSourceConfig({
        data_source: dataSource,
        realtime_data_source: realtimeDataSource,
        tushare_token: tushareToken.trim()
      })

      setSuccessMessage('数据源配置已保存')

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
        <Alert className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
          <AlertDescription className="text-green-800 dark:text-green-200">
            {successMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* 错误提示 */}
      {error && (
        <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <AlertDescription className="text-red-800 dark:text-red-200">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* 主数据源配置 */}
      <Card>
        <CardHeader>
          <CardTitle>主数据源配置</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            用于历史数据、股票列表等
          </p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          ) : (
            <div className="space-y-3">
              <RadioGroup value={dataSource} onValueChange={(value) => setDataSource(value as 'akshare' | 'tushare')}>
                {/* AkShare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  dataSource === 'akshare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <RadioGroupItem value="akshare" className="mt-1 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">AkShare</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                        免费
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      免费开源的 Python 金融数据接口，无需 Token
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>• 无需注册和积分</p>
                      <p>• 数据来源稳定（东方财富、新浪财经等）</p>
                      <p>• 存在 IP 限流风险，建议请求间隔 ≥ 0.3秒</p>
                    </div>
                  </div>
                </label>

                {/* Tushare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  dataSource === 'tushare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <RadioGroupItem value="tushare" className="mt-1 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">Tushare Pro</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                        需要积分
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      专业的金融数据接口，数据质量高、覆盖全面
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>• 数据质量高，覆盖全面</p>
                      <p>• 需要积分：日线数据 120 分、分钟数据 2000 分</p>
                      <p>• 有频率限制（与积分等级相关）</p>
                    </div>
                  </div>
                </label>
              </RadioGroup>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tushare Token 配置 - 仅在至少一个数据源选择Tushare时显示 */}
      {!isLoading && (dataSource === 'tushare' || realtimeDataSource === 'tushare') && (
        <Card className="border-yellow-200 dark:border-yellow-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Tushare API Token
              <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                必填
              </span>
            </CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
              使用 Tushare 数据源时必须提供 API Token
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="tushare-token">API Token</Label>
            <Input
              id="tushare-token"
              type="text"
              value={tushareToken}
              onChange={(e) => setTushareToken(e.target.value)}
              placeholder="请输入您的 Tushare Token"
              className="font-mono"
            />
            <p className="text-xs text-gray-600 dark:text-gray-400">
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
          </CardContent>
        </Card>
      )}

      {/* 实时数据源配置 */}
      {!isLoading && (
        <Card>
          <CardHeader>
            <CardTitle>实时数据源配置</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
              用于实时行情数据获取
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <RadioGroup value={realtimeDataSource} onValueChange={(value) => setRealtimeDataSource(value as 'akshare' | 'tushare')}>
                {/* AkShare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  realtimeDataSource === 'akshare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <RadioGroupItem value="akshare" className="mt-1 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">AkShare</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                        推荐
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      免费获取实时行情，无需积分限制
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>• 获取速度：3-5分钟（分批次爬取）</p>
                      <p>• 无积分要求，适合普通用户</p>
                    </div>
                  </div>
                </label>

                {/* Tushare 选项 */}
                <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  realtimeDataSource === 'tushare'
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  <RadioGroupItem value="tushare" className="mt-1 mr-3" />
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900 dark:text-white">Tushare Pro</span>
                      <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                        需要5000积分
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      需要高积分等级才能访问实时行情接口
                    </p>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <p>• 获取速度：较快</p>
                      <p>• 需要 5000 积分才能访问</p>
                    </div>
                  </div>
                </label>
              </RadioGroup>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 保存按钮 */}
      {!isLoading && (
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? '保存中...' : '保存配置'}
          </Button>
        </div>
      )}

    </div>
  )
}
