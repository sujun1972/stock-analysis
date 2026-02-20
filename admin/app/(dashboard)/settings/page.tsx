'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useConfigStore } from '@/stores/config-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export default function SettingsPage() {
  const { dataSource: configData, isLoading, error: configError, fetchDataSourceConfig } = useConfigStore()

  const [dataSource, setDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [minuteDataSource, setMinuteDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [realtimeDataSource, setRealtimeDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [tushareToken, setTushareToken] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // 只在首次挂载时加载配置
  useEffect(() => {
    fetchDataSourceConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 当配置加载完成后,更新本地状态
  useEffect(() => {
    if (configData) {
      setDataSource(configData.data_source as 'akshare' | 'tushare')
      setMinuteDataSource(configData.minute_data_source as 'akshare' | 'tushare')
      setRealtimeDataSource(configData.realtime_data_source as 'akshare' | 'tushare')
      setTushareToken(configData.tushare_token || '')
    }
  }, [configData])

  // 设置错误消息
  useEffect(() => {
    if (configError) {
      setError(configError)
    }
  }, [configError])

  const handleSave = async () => {
    try {
      setIsSaving(true)
      setError(null)
      setSuccessMessage(null)

      // 验证：如果任一数据源选择 Tushare，必须提供 Token
      if ((dataSource === 'tushare' || minuteDataSource === 'tushare' || realtimeDataSource === 'tushare') && !tushareToken.trim()) {
        setError('使用 Tushare 数据源需要提供 API Token')
        return
      }

      await apiClient.updateDataSourceConfig({
        data_source: dataSource,
        minute_data_source: minuteDataSource,
        realtime_data_source: realtimeDataSource,
        tushare_token: tushareToken.trim()
      })

      // 更新Store中的缓存
      fetchDataSourceConfig(true)

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

      {/* 数据源配置卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>数据源配置</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            配置不同类型数据的数据源，支持 AkShare（免费）和 Tushare Pro（需积分）
          </p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 主数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="data-source">主数据源</Label>
                <Select value={dataSource} onValueChange={(value) => setDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="data-source">
                    <SelectValue placeholder="选择主数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          免费
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                          需120积分
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于历史数据、股票列表等
                </p>
              </div>

              {/* 分时数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="minute-data-source">分时数据源</Label>
                <Select value={minuteDataSource} onValueChange={(value) => setMinuteDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="minute-data-source">
                    <SelectValue placeholder="选择分时数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          推荐
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                          需2000积分
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于分时K线数据获取（1分钟、5分钟、15分钟等）
                </p>
              </div>

              {/* 实时数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="realtime-data-source">实时数据源</Label>
                <Select value={realtimeDataSource} onValueChange={(value) => setRealtimeDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="realtime-data-source">
                    <SelectValue placeholder="选择实时数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          推荐
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                          需5000积分
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于实时行情数据获取
                </p>
              </div>

              {/* Tushare Token - 仅在至少一个数据源选择Tushare时显示 */}
              {(dataSource === 'tushare' || minuteDataSource === 'tushare' || realtimeDataSource === 'tushare') && (
                <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="tushare-token">Tushare API Token</Label>
                    <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                      必填
                    </span>
                  </div>
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
                </div>
              )}

              {/* 保存按钮 */}
              <div className="flex justify-end pt-4">
                <Button
                  onClick={handleSave}
                  disabled={isSaving}
                >
                  {isSaving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      </div>
  )
}
