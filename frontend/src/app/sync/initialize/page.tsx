'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DatePicker } from '@/components/ui/date-picker'
import { format, subDays, subMonths, subYears } from 'date-fns'

/**
 * 模块同步状态接口（用于股票列表同步）
 */
interface ModuleSyncStatus {
  status: string
  total: number
  success: number
  failed: number
  progress: number
  error_message: string
  started_at: string
  completed_at: string
}

/**
 * 全局同步状态接口（用于日线数据同步）
 */
interface SyncStatus {
  status: string
  last_sync_date: string
  progress: number
  total: number
  completed: number
}

export default function InitializePage() {
  const router = useRouter()

  // ========== 股票列表同步相关状态 ==========
  const [stockListStatus, setStockListStatus] = useState<ModuleSyncStatus | null>(null)
  const [isStockListLoading, setIsStockListLoading] = useState(false)
  const [stockListError, setStockListError] = useState<string | null>(null)
  const [stockListSuccess, setStockListSuccess] = useState<string | null>(null)

  // ========== 日线数据同步相关状态 ==========
  const [dailySyncStatus, setDailySyncStatus] = useState<SyncStatus | null>(null)
  const [isDailyLoading, setIsDailyLoading] = useState(false)
  const [dailyError, setDailyError] = useState<string | null>(null)
  const [dailySuccess, setDailySuccess] = useState<string | null>(null)

  // 日线数据同步参数 - 使用日期范围
  const [startDate, setStartDate] = useState<Date>(() => subDays(new Date(), 3)) // 默认3天前
  const [endDate, setEndDate] = useState<Date>(new Date()) // 默认今天
  const [datePreset, setDatePreset] = useState<string>('3days') // 默认预设：3天历史

  // 预设日期范围映射
  const applyDatePreset = (preset: string) => {
    const today = new Date()
    setEndDate(today)

    switch (preset) {
      case '3days':
        setStartDate(subDays(today, 3))
        break
      case '1month':
        setStartDate(subMonths(today, 1))
        break
      case '3years':
        setStartDate(subYears(today, 3))
        break
      case '5years':
        setStartDate(subYears(today, 5))
        break
      case '10years':
        setStartDate(subYears(today, 10))
        break
    }
  }

  // 当预设改变时应用
  useEffect(() => {
    applyDatePreset(datePreset)
  }, [datePreset])

  // ========== 股票列表同步逻辑 ==========
  useEffect(() => {
    loadStockListStatus()
    const interval = setInterval(() => {
      if (stockListStatus?.status === 'running') {
        loadStockListStatus()
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [stockListStatus?.status])

  const loadStockListStatus = async () => {
    try {
      const response = await apiClient.getModuleSyncStatus('stock_list')
      if (response.data) {
        setStockListStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load stock list status:', err)
    }
  }

  const handleStockListSync = async () => {
    setIsStockListLoading(true)
    setStockListError(null)
    setStockListSuccess(null)

    // 启动同步请求（不等待完成）
    apiClient.syncStockList()
      .then((response) => {
        if (response.data) {
          setStockListSuccess(`成功同步股票列表！共获取 ${response.data.total || 0} 只股票`)
          setTimeout(() => setStockListSuccess(null), 5000)
        }
        setIsStockListLoading(false)
      })
      .catch((err: any) => {
        const errorMessage = err.response?.data?.detail || err.message || '同步股票列表失败'
        setStockListError(errorMessage)
        console.error('Stock list sync error:', err)
        setIsStockListLoading(false)
      })

    // 立即开始轮询状态（每2秒一次）
    const pollInterval = setInterval(async () => {
      await loadStockListStatus()
      if (stockListStatus?.status && stockListStatus.status !== 'running') {
        clearInterval(pollInterval)
      }
    }, 2000)

    // 30秒后强制停止轮询（防止无限轮询）
    setTimeout(() => clearInterval(pollInterval), 30000)
  }

  // ========== 日线数据同步逻辑 ==========
  useEffect(() => {
    loadDailySyncStatus()
    const interval = setInterval(() => {
      if (dailySyncStatus?.status === 'running') {
        loadDailySyncStatus()
      }
    }, 3000) // 每3秒刷新一次进度
    return () => clearInterval(interval)
  }, [dailySyncStatus?.status])

  const loadDailySyncStatus = async () => {
    try {
      const response = await apiClient.getSyncStatus()
      if (response.data) {
        setDailySyncStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load daily sync status:', err)
    }
  }

  const handleDailySync = async () => {
    try {
      setIsDailyLoading(true)
      setDailyError(null)
      setDailySuccess(null)

      // 立即更新状态为同步中
      setDailySyncStatus({
        status: 'running',
        last_sync_date: dailySyncStatus?.last_sync_date || '',
        progress: 0,
        total: 0,
        completed: 0
      })

      // 格式化日期为 YYYY-MM-DD
      const formattedStartDate = format(startDate, 'yyyy-MM-dd')
      const formattedEndDate = format(endDate, 'yyyy-MM-dd')

      const response = await apiClient.syncDailyBatch({
        start_date: formattedStartDate,
        end_date: formattedEndDate
      })

      if (response.data) {
        const { success, failed, skipped, total, aborted } = response.data
        const skipMsg = skipped > 0 ? `，跳过: ${skipped} 只（数据已完整）` : ''
        const abortMsg = aborted ? '（已中止）' : ''
        setDailySuccess(`同步完成${abortMsg}！成功: ${success} 只，失败: ${failed} 只${skipMsg}，总计: ${total} 只`)
      }

      // 重新加载最新状态
      await loadDailySyncStatus()

      setTimeout(() => setDailySuccess(null), 8000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '批量同步日线数据失败'
      setDailyError(errorMessage)
      console.error('Daily sync error:', err)

      // 重置状态
      await loadDailySyncStatus()
    } finally {
      setIsDailyLoading(false)
    }
  }

  const handleAbortSync = async () => {
    try {
      await apiClient.abortSync()
      setDailySuccess('正在中止同步，请稍候...')
      setTimeout(() => setDailySuccess(null), 5000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '中止同步失败'
      setDailyError(errorMessage)
      console.error('Abort sync error:', err)
      setTimeout(() => setDailyError(null), 5000)
    }
  }

  // ========== 工具函数 ==========
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'aborted': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '同步中'
      case 'completed': return '已完成'
      case 'failed': return '失败'
      case 'aborted': return '已中止'
      default: return '空闲'
    }
  }

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <div>
        <Button variant="ghost" onClick={() => router.back()}>
          ← 返回数据同步管理
        </Button>
      </div>

      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          数据初始化
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          系统首次使用时的必要步骤，请按顺序完成以下初始化操作
        </p>
      </div>

      {/* 使用建议 */}
      <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle className="text-lg text-blue-900 dark:text-blue-200">
            使用建议
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-300">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>建议先完成<strong>步骤1（股票列表初始化）</strong>，再进行步骤2</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>首次使用建议选择较短时间范围（如3天或1个月）进行测试</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>大批量同步建议在非交易时段进行，避免影响数据源性能</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>系统会自动过滤退市和停牌股票，只同步正常交易的股票</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* ========== 步骤1: 股票列表初始化 ========== */}
      <Card className="border-2 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <div className="flex items-center">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-600 text-white font-bold mr-3">
              1
            </div>
            <CardTitle className="text-xl">
              股票列表初始化
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            获取A股市场所有股票基本信息（约5000+只），包括股票代码、名称、行业、地区等
          </p>

          {/* 错误提示 */}
          {stockListError && (
            <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
              <AlertDescription className="text-red-800 dark:text-red-200">
                {stockListError}
              </AlertDescription>
            </Alert>
          )}

          {/* 成功提示 */}
          {stockListSuccess && (
            <Alert className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
              <AlertDescription className="text-green-800 dark:text-green-200">
                {stockListSuccess}
              </AlertDescription>
            </Alert>
          )}

          {/* 上次同步信息 */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">上次同步信息</h3>
            {stockListStatus ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">状态</div>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(stockListStatus.status)}`}>
                      {getStatusText(stockListStatus.status)}
                    </span>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">开始时间</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {stockListStatus.started_at || '未同步'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成时间</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {stockListStatus.completed_at || '-'}
                    </div>
                  </div>
                </div>

                {stockListStatus.status === 'completed' && stockListStatus.success > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">同步总数</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {stockListStatus.total || 0} 只
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">成功</div>
                      <div className="font-medium text-green-600 dark:text-green-400">
                        {stockListStatus.success || 0} 只
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">失败</div>
                      <div className="font-medium text-red-600 dark:text-red-400">
                        {stockListStatus.failed || 0} 只
                      </div>
                    </div>
                  </div>
                )}

                {stockListStatus.error_message && (
                  <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
                    <AlertDescription className="text-sm text-red-900 dark:text-red-200">
                      <div className="font-medium mb-1">错误详情：</div>
                      <div className="whitespace-pre-wrap">{stockListStatus.error_message}</div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            ) : (
              <div className="text-gray-600 dark:text-gray-400 text-sm">加载状态中...</div>
            )}
          </div>

          {/* 开始同步按钮 */}
          <Button
            onClick={handleStockListSync}
            disabled={isStockListLoading || stockListStatus?.status === 'running'}
            className="w-full md:w-auto"
          >
            {isStockListLoading || stockListStatus?.status === 'running' ? '同步中...' : '开始同步股票列表'}
          </Button>

          {/* 数据说明 */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                查看数据说明
              </summary>
              <div className="mt-3 space-y-2 text-gray-600 dark:text-gray-400">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <strong className="text-gray-700 dark:text-gray-300">数据内容：</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>股票代码、名称</li>
                      <li>市场类型</li>
                      <li>所属行业、地区</li>
                      <li>上市日期</li>
                    </ul>
                  </div>
                  <div>
                    <strong className="text-gray-700 dark:text-gray-300">注意事项：</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>建议每月更新一次</li>
                      <li>同步会覆盖更新现有数据</li>
                      <li>通常需要几秒到几分钟</li>
                    </ul>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </CardContent>
      </Card>

      {/* ========== 步骤2: 日线数据初始化 ========== */}
      <Card className="border-2 border-purple-200 dark:border-purple-800">
        <CardHeader>
          <div className="flex items-center">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-purple-600 text-white font-bold mr-3">
              2
            </div>
            <CardTitle className="text-xl">
              日线数据初始化
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            批量同步所有正常股票的历史日线数据（自动过滤退市和停牌股票）
          </p>

          {/* 错误提示 */}
          {dailyError && (
            <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
              <AlertDescription className="text-red-800 dark:text-red-200">
                {dailyError}
              </AlertDescription>
            </Alert>
          )}

          {/* 成功提示 */}
          {dailySuccess && (
            <Alert className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
              <AlertDescription className="text-green-800 dark:text-green-200">
                {dailySuccess}
              </AlertDescription>
            </Alert>
          )}

          {/* 当前同步状态 */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">当前同步状态</h3>
            {dailySyncStatus ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">状态</div>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(dailySyncStatus.status)}`}>
                      {getStatusText(dailySyncStatus.status)}
                    </span>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">最后同步</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {dailySyncStatus.last_sync_date || '未同步'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">进度</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {dailySyncStatus.completed} / {dailySyncStatus.total}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成率</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {dailySyncStatus.progress}%
                    </div>
                  </div>
                </div>

                {/* 进度条 */}
                {dailySyncStatus.status === 'running' && (
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-purple-600 h-3 rounded-full transition-all duration-300 flex items-center justify-center text-xs text-white"
                      style={{ width: `${dailySyncStatus.progress}%` }}
                    >
                      {dailySyncStatus.progress > 10 && `${dailySyncStatus.progress}%`}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-600 dark:text-gray-400 text-sm">加载状态中...</div>
            )}
          </div>

          {/* 同步参数配置 */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">同步参数配置</h3>

            {/* 快捷预设 */}
            <div className="space-y-2">
              <Label htmlFor="preset">历史数据范围预设</Label>
              <Select value={datePreset} onValueChange={setDatePreset} disabled={isDailyLoading || dailySyncStatus?.status === 'running'}>
                <SelectTrigger id="preset" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3days">3天历史（推荐测试）</SelectItem>
                  <SelectItem value="1month">1个月历史</SelectItem>
                  <SelectItem value="3years">3年历史</SelectItem>
                  <SelectItem value="5years">5年历史（推荐）</SelectItem>
                  <SelectItem value="10years">10年历史</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                选择预设后，起始日期和结束日期会自动更新
              </p>
            </div>

            {/* 日期范围选择 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>起始日期</Label>
                <DatePicker
                  date={startDate}
                  onDateChange={(date) => date && setStartDate(date)}
                  placeholder="选择起始日期"
                  disabled={isDailyLoading || dailySyncStatus?.status === 'running'}
                />
              </div>
              <div className="space-y-2">
                <Label>结束日期</Label>
                <DatePicker
                  date={endDate}
                  onDateChange={(date) => date && setEndDate(date)}
                  placeholder="选择结束日期"
                  disabled={isDailyLoading || dailySyncStatus?.status === 'running'}
                />
              </div>
            </div>

            {/* 日期范围提示 */}
            <Alert className="bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800">
              <AlertDescription className="text-sm text-purple-800 dark:text-purple-300">
                <strong>当前选择：</strong>从 {format(startDate, 'yyyy年MM月dd日')} 至 {format(endDate, 'yyyy年MM月dd日')}
                <br />
                <strong>同步范围：</strong>所有正常状态股票（自动排除退市、停牌股票）
              </AlertDescription>
            </Alert>
          </div>

          {/* 开始同步和中止按钮 */}
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={handleDailySync}
              disabled={isDailyLoading || dailySyncStatus?.status === 'running'}
              className="flex-1 md:flex-initial md:w-auto"
            >
              {isDailyLoading || dailySyncStatus?.status === 'running' ? '同步中...' : '开始批量同步'}
            </Button>

            {(isDailyLoading || dailySyncStatus?.status === 'running') && (
              <Button
                onClick={handleAbortSync}
                variant="destructive"
                className="flex-1 md:flex-initial md:w-auto"
              >
                中止同步
              </Button>
            )}
          </div>

          {/* 数据说明 */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                查看数据说明
              </summary>
              <div className="mt-3 space-y-2 text-gray-600 dark:text-gray-400">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <strong className="text-gray-700 dark:text-gray-300">数据内容：</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>开盘价、收盘价</li>
                      <li>最高价、最低价</li>
                      <li>成交量、成交额</li>
                      <li>涨跌幅、振幅</li>
                    </ul>
                  </div>
                  <div>
                    <strong className="text-gray-700 dark:text-gray-300">注意事项：</strong>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>同步过程中不要关闭浏览器</li>
                      <li>同步会覆盖更新现有数据</li>
                      <li>注意API限流问题</li>
                      <li>自动过滤退市和停牌股票</li>
                    </ul>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </CardContent>
      </Card>

      {/* 注意事项 */}
      <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
        <CardHeader>
          <CardTitle className="text-lg text-yellow-900 dark:text-yellow-200">
            重要提示
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-yellow-800 dark:text-yellow-300">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>数据源可在系统设置中切换（AkShare 或 Tushare）</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>完成初始化后，建议配置定时任务实现数据自动更新</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>如遇到大量失败，建议减小日期范围或稍后重试</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>系统会自动检查数据完整性，已有完整数据的股票会被跳过</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
