'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

interface SyncStatus {
  status: string
  last_sync_date: string
  progress: number
  total: number
  completed: number
}

export default function DailySyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // 同步参数
  const [maxStocks, setMaxStocks] = useState<number>(100)
  const [years, setYears] = useState<number>(5)

  useEffect(() => {
    loadSyncStatus()
    const interval = setInterval(() => {
      if (syncStatus?.status === 'running') {
        loadSyncStatus()
      }
    }, 3000) // 每3秒刷新一次进度
    return () => clearInterval(interval)
  }, [syncStatus?.status])

  const loadSyncStatus = async () => {
    try {
      const response = await apiClient.getSyncStatus()
      if (response.data) {
        setSyncStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load sync status:', err)
    }
  }

  const handleSync = async () => {
    try {
      setIsLoading(true)
      setError(null)
      setSuccessMessage(null)

      // 立即更新状态为同步中
      setSyncStatus({
        status: 'running',
        last_sync_date: syncStatus?.last_sync_date || '',
        progress: 0,
        total: maxStocks,
        completed: 0
      })

      const response = await apiClient.syncDailyBatch({
        years,
        max_stocks: maxStocks
      })

      if (response.data) {
        const { success, failed, total } = response.data
        setSuccessMessage(`同步完成！成功: ${success} 只，失败: ${failed} 只，总计: ${total} 只`)
      }

      // 重新加载最新状态
      await loadSyncStatus()

      setTimeout(() => setSuccessMessage(null), 8000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '批量同步日线数据失败'
      setError(errorMessage)
      console.error('Sync error:', err)

      // 重置状态
      await loadSyncStatus()
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '同步中'
      case 'completed': return '已完成'
      case 'failed': return '失败'
      default: return '空闲'
    }
  }

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <button
        onClick={() => router.back()}
        className="text-blue-600 dark:text-blue-400 hover:underline flex items-center"
      >
        ← 返回同步管理
      </button>

      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          📊 日线数据同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          批量同步股票的历史日线数据（OHLCV - 开高低收成交量），支持自定义时间范围和股票数量
        </p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* 成功提示 */}
      {successMessage && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="text-green-800 dark:text-green-200">{successMessage}</p>
        </div>
      )}

      {/* 当前同步状态 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          当前同步状态
        </h2>
        {syncStatus ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">状态</div>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(syncStatus.status)}`}>
                  {getStatusText(syncStatus.status)}
                </span>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">最后同步</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {syncStatus.last_sync_date || '未同步'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">进度</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {syncStatus.completed} / {syncStatus.total}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成率</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {syncStatus.progress}%
                </div>
              </div>
            </div>

            {/* 进度条 */}
            {syncStatus.status === 'running' && (
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300 flex items-center justify-center text-xs text-white"
                  style={{ width: `${syncStatus.progress}%` }}
                >
                  {syncStatus.progress > 10 && `${syncStatus.progress}%`}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-600 dark:text-gray-400">加载状态中...</div>
        )}
      </div>

      {/* 同步参数配置 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          同步参数配置
        </h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 股票数量 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                同步股票数量
              </label>
              <select
                value={maxStocks}
                onChange={(e) => setMaxStocks(Number(e.target.value))}
                disabled={isLoading || syncStatus?.status === 'running'}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value={10}>10 只（快速测试）</option>
                <option value={50}>50 只（小批量）</option>
                <option value={100}>100 只（推荐）</option>
                <option value={500}>500 只（中批量）</option>
                <option value={1000}>1000 只（大批量）</option>
                <option value={5000}>全部股票（约 5000+ 只，耗时较长）</option>
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                首次使用建议选择 10-100 只进行测试
              </p>
            </div>

            {/* 历史年数 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                历史数据年限
              </label>
              <select
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                disabled={isLoading || syncStatus?.status === 'running'}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value={1}>1 年</option>
                <option value={3}>3 年</option>
                <option value={5}>5 年（推荐）</option>
                <option value={10}>10 年</option>
                <option value={20}>20 年（全部历史数据）</option>
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                年限越长，数据量越大，同步时间越久
              </p>
            </div>
          </div>

          {/* 预估时间提示 */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-sm text-blue-800 dark:text-blue-300">
              <strong>预估同步时间：</strong>
              {maxStocks <= 10 && ' 约 30秒 - 1分钟'}
              {maxStocks > 10 && maxStocks <= 50 && ' 约 2-3 分钟'}
              {maxStocks > 50 && maxStocks <= 100 && ' 约 5-8 分钟'}
              {maxStocks > 100 && maxStocks <= 500 && ' 约 20-40 分钟'}
              {maxStocks > 500 && maxStocks <= 1000 && ' 约 1-2 小时'}
              {maxStocks > 1000 && ' 约 3-5 小时或更长'}
            </p>
          </div>

          {/* 开始同步按钮 */}
          <button
            onClick={handleSync}
            disabled={isLoading || syncStatus?.status === 'running'}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading || syncStatus?.status === 'running' ? '同步中...' : '开始批量同步'}
          </button>
        </div>
      </div>

      {/* 数据说明 */}
      <div className="card bg-gray-50 dark:bg-gray-800">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          📊 数据说明
        </h3>
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <strong>数据内容：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>日期（交易日）</li>
                <li>开盘价、收盘价</li>
                <li>最高价、最低价</li>
                <li>成交量、成交额</li>
                <li>涨跌幅、振幅</li>
                <li>换手率（部分数据源）</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>技术指标计算（MA、MACD、KDJ 等）</li>
                <li>量价分析</li>
                <li>趋势判断</li>
                <li>回测系统基础数据</li>
                <li>特征工程</li>
                <li>机器学习训练</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 注意事项 */}
      <div className="card bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
        <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-200 mb-3">
          ⚠️ 注意事项
        </h3>
        <ul className="space-y-2 text-sm text-yellow-800 dark:text-yellow-300">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>日线数据量较大，<strong>首次使用建议从少量股票开始测试</strong>（10-100 只）</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>同步过程中请<strong>不要关闭浏览器</strong>，大批量同步可能需要数小时</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>同步会<strong>覆盖更新</strong>现有数据，确保数据最新（增量同步）</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>请注意 <strong>API 限流</strong>：AkShare 有 IP 限制，Tushare 有积分和频率限制</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>如遇到大量失败，建议<strong>减少批量大小</strong>或稍后重试</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>单个股票数据获取超时时间为 30 秒，超时会自动跳过</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据源可在<a href="/settings" className="underline">系统设置</a>中切换（AkShare 或 Tushare）</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
