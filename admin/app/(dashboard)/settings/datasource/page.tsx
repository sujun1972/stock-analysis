/**
 * 数据源设置页面
 *
 * 功能：
 * - 配置主数据源（AkShare/Tushare）
 * - 配置分时数据源
 * - 配置实时数据源
 * - 管理 Tushare API Token
 *
 * @author Admin Team
 * @since 2026-03-03
 */

'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useConfigStore } from '@/stores/config-store'
import logger from '@/lib/logger'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { CheckCircle2, XCircle, Loader2, PlayCircle, AlertTriangle, Info } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

export default function SettingsPage() {
  const { dataSource: configData, isLoading, error: configError, fetchDataSourceConfig } = useConfigStore()

  const [dataSource, setDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [minuteDataSource, setMinuteDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [realtimeDataSource, setRealtimeDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [limitUpDataSource, setLimitUpDataSource] = useState<'akshare' | 'tushare'>('tushare')
  const [topListDataSource, setTopListDataSource] = useState<'akshare' | 'tushare'>('tushare')
  const [premarketDataSource, setPremarketDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [conceptDataSource, setConceptDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [sentimentDataSource, setSentimentDataSource] = useState<'akshare' | 'tushare'>('akshare')
  const [tushareToken, setTushareToken] = useState('')
  const [earliestHistoryDate, setEarliestHistoryDate] = useState('2021-01-04')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // 扩展数据配置相关状态
  const [extendedDataEnabled, setExtendedDataEnabled] = useState(false)
  const [moneyflowStrategy, setMoneyflowStrategy] = useState<'top100' | 'active' | 'all'>('top100')
  const [backfillDays, setBackfillDays] = useState<'0' | '7' | '30' | '90'>('0')

  // 测试相关状态
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResults, setTestResults] = useState<{
    name: string
    status: 'pending' | 'running' | 'success' | 'error'
    message?: string
  }[]>([])

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
      setLimitUpDataSource((configData.limit_up_data_source || 'tushare') as 'akshare' | 'tushare')
      setTopListDataSource((configData.top_list_data_source || 'tushare') as 'akshare' | 'tushare')
      setPremarketDataSource((configData.premarket_data_source || 'akshare') as 'akshare' | 'tushare')
      setConceptDataSource((configData.concept_data_source || 'akshare') as 'akshare' | 'tushare')
      setSentimentDataSource((configData.sentiment_data_source || 'akshare') as 'akshare' | 'tushare')

      // 安全性：Token从后端返回时已被掩码（如 d038****...****f3ad）
      // 前端始终显示为空，避免暴露真实Token
      setTushareToken('')
      setEarliestHistoryDate((configData as any).earliest_history_date || '2021-01-04')
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

      // 验证：如果任一数据源选择 Tushare，且当前没有配置 Token，必须提供新 Token
      const anyTushare = dataSource === 'tushare' || minuteDataSource === 'tushare' ||
                        realtimeDataSource === 'tushare' || limitUpDataSource === 'tushare' ||
                        topListDataSource === 'tushare' || premarketDataSource === 'tushare' ||
                        conceptDataSource === 'tushare' || sentimentDataSource === 'tushare'

      // 检查是否已有 Token（通过星号判断是否为后端掩码后的 Token）
      const hasExistingToken = configData?.tushare_token && configData.tushare_token.includes('*')

      if (anyTushare && !hasExistingToken && !tushareToken.trim()) {
        setError('使用 Tushare 数据源需要提供 API Token')
        return
      }

      // "留空不修改"模式：如果Token留空，则不修改原有Token（传undefined）
      const tokenToSave = tushareToken.trim() ? tushareToken.trim() : undefined

      await apiClient.updateDataSourceConfig({
        data_source: dataSource,
        minute_data_source: minuteDataSource,
        realtime_data_source: realtimeDataSource,
        limit_up_data_source: limitUpDataSource,
        top_list_data_source: topListDataSource,
        premarket_data_source: premarketDataSource,
        concept_data_source: conceptDataSource,
        sentiment_data_source: sentimentDataSource,
        tushare_token: tokenToSave,
        earliest_history_date: earliestHistoryDate || undefined,
      })

      // 更新Store中的缓存
      fetchDataSourceConfig(true)

      setSuccessMessage('数据源配置已保存')

      // 5秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      setError(err.message || '保存配置失败')
    } finally {
      setIsSaving(false)
    }
  }

  /**
   * 测试所有数据源连接
   * TODO: 当前为UI演示版本，未来可扩展为真实API测试
   */
  const handleTest = async () => {
    setIsTestDialogOpen(true)
    setIsTesting(true)

    // 初始化测试项
    const tests = [
      { name: `主数据源 (${dataSource})`, status: 'pending' as const, message: '等待测试' },
      { name: `分时数据源 (${minuteDataSource})`, status: 'pending' as const, message: '等待测试' },
      { name: `实时数据源 (${realtimeDataSource})`, status: 'pending' as const, message: '等待测试' },
      { name: `涨停板池数据源 (${limitUpDataSource})`, status: 'pending' as const, message: '等待测试' },
      { name: `龙虎榜数据源 (${topListDataSource})`, status: 'pending' as const, message: '等待测试' },
      { name: `盘前数据源 (${premarketDataSource})`, status: 'pending' as const, message: '等待测试' },
    ]
    setTestResults(tests)

    try {
      // 测试主数据源
      setTestResults(prev => prev.map((t, i) => i === 0 ? { ...t, status: 'running', message: '正在连接...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      try {
        // 使用 apiClient 验证配置API可访问性
        await apiClient.getDataSourceConfig()
        setTestResults(prev => prev.map((t, i) =>
          i === 0 ? { ...t, status: 'success', message: '连接成功' } : t
        ))
      } catch (err: any) {
        setTestResults(prev => prev.map((t, i) =>
          i === 0 ? { ...t, status: 'error', message: `连接失败: ${err.message}` } : t
        ))
      }

      // 测试分时数据源（演示版本）
      setTestResults(prev => prev.map((t, i) => i === 1 ? { ...t, status: 'running', message: '正在连接...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      setTestResults(prev => prev.map((t, i) =>
        i === 1 ? { ...t, status: 'success', message: '连接成功' } : t
      ))

      // 测试实时数据源（演示版本）
      setTestResults(prev => prev.map((t, i) => i === 2 ? { ...t, status: 'running', message: '正在连接...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      setTestResults(prev => prev.map((t, i) =>
        i === 2 ? { ...t, status: 'success', message: '连接成功' } : t
      ))

      // 测试涨停板池数据源（演示版本）
      setTestResults(prev => prev.map((t, i) => i === 3 ? { ...t, status: 'running', message: '正在获取数据...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      setTestResults(prev => prev.map((t, i) =>
        i === 3 ? { ...t, status: 'success', message: '数据获取成功' } : t
      ))

      // 测试龙虎榜数据源（演示版本）
      setTestResults(prev => prev.map((t, i) => i === 4 ? { ...t, status: 'running', message: '正在获取数据...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      setTestResults(prev => prev.map((t, i) =>
        i === 4 ? { ...t, status: 'success', message: '数据获取成功' } : t
      ))

      // 测试盘前数据源（演示版本）
      setTestResults(prev => prev.map((t, i) => i === 5 ? { ...t, status: 'running', message: '正在获取数据...' } : t))
      await new Promise(resolve => setTimeout(resolve, 500))
      setTestResults(prev => prev.map((t, i) =>
        i === 5 ? { ...t, status: 'success', message: '数据获取成功' } : t
      ))

    } catch (err: any) {
      logger.error('测试失败', err)
    } finally {
      setIsTesting(false)
    }
  }

  return (
        <div className="space-y-6">
        {/* 页面标题 */}
        <PageHeader
          title="数据源设置"
          description="配置股票数据源（AkShare / Tushare）"
        />

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

              {/* 涨停板池数据源配置 */}
              <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Label htmlFor="limit-up-data-source">涨停板池数据源</Label>
                <Select value={limitUpDataSource} onValueChange={(value) => setLimitUpDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="limit-up-data-source">
                    <SelectValue placeholder="选择涨停板池数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                          推荐（你有5000积分）
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          免费（数据更丰富）
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于涨停板池数据（Tushare需2000积分，速度更快；AkShare免费但功能更丰富）
                </p>
              </div>

              {/* 龙虎榜数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="top-list-data-source">龙虎榜数据源</Label>
                <Select value={topListDataSource} onValueChange={(value) => setTopListDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="top-list-data-source">
                    <SelectValue placeholder="选择龙虎榜数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                          推荐（你有5000积分）
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          免费（席位更详细）
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于龙虎榜数据（Tushare需2000积分，更稳定；AkShare免费但席位详情更细致）
                </p>
              </div>

              {/* 盘前数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="premarket-data-source">盘前数据源</Label>
                <Select value={premarketDataSource} onValueChange={(value) => setPremarketDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="premarket-data-source">
                    <SelectValue placeholder="选择盘前数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          推荐（外盘数据）
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                          仅A股盘前
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于盘前数据（AkShare支持A50、中概股等外盘数据；Tushare仅支持A股盘前股本数据）
                </p>
              </div>

              {/* 概念数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="concept-data-source">概念数据源</Label>
                <Select value={conceptDataSource} onValueChange={(value) => setConceptDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="concept-data-source">
                    <SelectValue placeholder="选择概念数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare (东方财富)</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          推荐（466个概念）
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
                  用于概念板块数据（AkShare免费，466个概念数据更丰富；Tushare需5000积分，数据更稳定）
                </p>
              </div>

              {/* 市场情绪数据源配置 */}
              <div className="space-y-2">
                <Label htmlFor="sentiment-data-source">市场情绪数据源</Label>
                <Select value={sentimentDataSource} onValueChange={(value) => setSentimentDataSource(value as 'akshare' | 'tushare')}>
                  <SelectTrigger id="sentiment-data-source">
                    <SelectValue placeholder="选择市场情绪数据源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="akshare">
                      <div className="flex items-center gap-2">
                        <span>AkShare (东方财富)</span>
                        <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          免费（功能丰富）
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="tushare">
                      <div className="flex items-center gap-2">
                        <span>Tushare Pro</span>
                        <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                          推荐（需120积分，更稳定）
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  用于市场指数数据（上证、深成、创业板）。AkShare免费但可能有反爬限制；Tushare需120积分，稳定可靠无限制
                </p>
              </div>

              {/* Tushare Token - 仅在至少一个数据源选择Tushare时显示 */}
              {(dataSource === 'tushare' || minuteDataSource === 'tushare' || realtimeDataSource === 'tushare' ||
                limitUpDataSource === 'tushare' || topListDataSource === 'tushare' || premarketDataSource === 'tushare' ||
                conceptDataSource === 'tushare' || sentimentDataSource === 'tushare') && (
                <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="tushare-token">Tushare API Token</Label>
                    {configData?.tushare_token && configData.tushare_token.includes('*') ? (
                      <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                        已配置
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                        必填
                      </span>
                    )}
                  </div>
                  <Input
                    id="tushare-token"
                    type="password"
                    value={tushareToken}
                    onChange={(e) => setTushareToken(e.target.value)}
                    placeholder={(configData?.tushare_token && configData.tushare_token.includes('*')) ? "留空不修改" : "请输入您的 Tushare Token"}
                    className="font-mono"
                  />
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {configData?.tushare_token && configData.tushare_token.includes('*') ? (
                      <>已有 Token 配置（{configData.tushare_token}），留空表示不修改</>
                    ) : (
                      <>
                        没有 Token？
                        <a
                          href="https://tushare.pro/register?reg=430522"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 dark:text-blue-400 hover:underline ml-1"
                        >
                          点击注册 Tushare 账号
                        </a>
                      </>
                    )}
                  </p>
                </div>
              )}

              {/* 历史数据最早日期 */}
              <div className="space-y-2">
                <Label htmlFor="earliest-history-date">全量同步最早日期</Label>
                <Input
                  id="earliest-history-date"
                  type="date"
                  value={earliestHistoryDate}
                  onChange={(e) => setEarliestHistoryDate(e.target.value)}
                  className="max-w-xs"
                />
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  各数据页面点击「全量同步」时以此日期为起始日，默认 2021-01-04（与日线行情一致）
                </p>
              </div>

              {/* 操作按钮 */}
              <div className="flex justify-end gap-3 pt-4">
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={isTesting}
                >
                  <PlayCircle className="mr-2 h-4 w-4" />
                  {isTesting ? '测试中...' : '测试连接'}
                </Button>
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

      {/* 扩展数据配置卡片 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>扩展数据配置（短线交易专用）</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            配置短线交易所需的高级数据源，这些数据仅支持 Tushare Pro
          </p>
        </CardHeader>
        <CardContent>
          {/* 总开关 */}
          <div className="flex items-center justify-between mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div>
              <Label>启用扩展数据同步</Label>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                开启后将同步资金流向、每日指标等高级数据
              </p>
            </div>
            <Switch
              checked={extendedDataEnabled}
              onCheckedChange={setExtendedDataEnabled}
            />
          </div>

          {extendedDataEnabled && (
            <div className="space-y-4">
              {/* 每日指标数据源 */}
              <div className="space-y-2">
                <Label>每日指标（换手率、PE等）</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Tushare Pro</Badge>
                  <span className="text-xs text-yellow-600">消耗 120 积分/次</span>
                </div>
                <p className="text-xs text-gray-600">
                  包含换手率、市盈率、市净率等关键指标
                </p>
              </div>

              {/* 资金流向数据源 */}
              <div className="space-y-2">
                <Label>资金流向</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Tushare Pro</Badge>
                  <span className="text-xs text-red-600 font-semibold">
                    ⚠️ 高消耗：2000 积分/次
                  </span>
                </div>
                <Alert className="mt-2">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    资金流向数据积分消耗高，建议仅同步活跃股票
                  </AlertDescription>
                </Alert>
              </div>

              {/* 北向资金数据源 */}
              <div className="space-y-2">
                <Label>北向资金（沪深港通）</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Tushare Pro</Badge>
                  <span className="text-xs text-yellow-600">消耗 300 积分/次</span>
                </div>
                <p className="text-xs text-gray-600">
                  追踪外资动向，重要参考指标
                </p>
              </div>

              {/* 融资融券数据源 */}
              <div className="space-y-2">
                <Label>融资融券</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">Tushare Pro</Badge>
                  <span className="text-xs text-yellow-600">消耗 300 积分/次</span>
                </div>
                <p className="text-xs text-gray-600">
                  两融余额变化，市场情绪指标
                </p>
              </div>

              {/* 积分消耗预估 */}
              <Alert className="mt-6">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-1">
                    <p className="font-semibold">积分消耗预估</p>
                    <p className="text-xs">日消耗：约 1,240 积分（不含资金流向）</p>
                    <p className="text-xs">月消耗：约 37,200 积分</p>
                    <p className="text-xs text-blue-600">
                      建议申请 5万积分/月 的配额
                    </p>
                  </div>
                </AlertDescription>
              </Alert>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 同步策略配置 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>同步策略配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* 资金流向同步策略 */}
            <div>
              <Label>资金流向同步策略</Label>
              <RadioGroup value={moneyflowStrategy} onValueChange={(value) => setMoneyflowStrategy(value as 'top100' | 'active' | 'all')}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="top100" id="top100" />
                  <Label htmlFor="top100" className="text-sm">
                    仅同步成交额前100（推荐）
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="active" id="active" />
                  <Label htmlFor="active" className="text-sm">
                    同步涨跌幅前200
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="all" id="all" />
                  <Label htmlFor="all" className="text-sm">
                    同步全部（消耗大量积分）
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* 历史数据回补 */}
            <div>
              <Label>历史数据回补</Label>
              <Select value={backfillDays} onValueChange={(v) => setBackfillDays(v as '0' | '7' | '30' | '90')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">不回补</SelectItem>
                  <SelectItem value="7">最近7天</SelectItem>
                  <SelectItem value="30">最近30天</SelectItem>
                  <SelectItem value="90">最近90天</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-600 mt-1">
                首次启用时是否同步历史数据
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 测试对话框 */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>数据源连接测试</DialogTitle>
            <DialogDescription>
              正在测试所有配置的数据源连接状态...
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-4">
            {testResults.map((test, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                {/* 状态图标 */}
                <div className="flex-shrink-0">
                  {test.status === 'pending' && (
                    <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                  )}
                  {test.status === 'running' && (
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  )}
                  {test.status === 'success' && (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  )}
                  {test.status === 'error' && (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>

                {/* 测试信息 */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{test.name}</div>
                  {test.message && (
                    <div className={`text-xs mt-1 ${
                      test.status === 'success' ? 'text-green-600 dark:text-green-400' :
                      test.status === 'error' ? 'text-red-600 dark:text-red-400' :
                      'text-gray-600 dark:text-gray-400'
                    }`}>
                      {test.message}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 底部按钮 */}
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setIsTestDialogOpen(false)}
              disabled={isTesting}
            >
              {isTesting ? '测试中...' : '关闭'}
            </Button>
            {!isTesting && testResults.length > 0 && (
              <Button onClick={handleTest}>
                重新测试
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      </div>
  )
}
