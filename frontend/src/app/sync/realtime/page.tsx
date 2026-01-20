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

export default function RealtimeSyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    loadSyncStatus()
  }, [])

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

      const response = await apiClient.syncRealtimeQuotes()

      if (response.data) {
        const { total, updated_at } = response.data
        setSuccessMessage(`成功获取实时行情！共 ${total} 只股票，更新时间: ${updated_at}`)
      }

      await loadSyncStatus()
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '获取实时行情失败'
      setError(errorMessage)
      console.error('Sync error:', err)
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
          ⚡ 实时行情同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          获取最新的实时行情快照，包括当前价格、涨跌幅、成交量等关键指标
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
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">股票总数</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.total || 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成率</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.progress}%
              </div>
            </div>
          </div>
        ) : (
          <div className="text-gray-600 dark:text-gray-400">加载状态中...</div>
        )}
      </div>

      {/* 同步操作 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          获取实时行情
        </h2>
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            点击下方按钮获取所有 A 股的最新实时行情快照。此操作会获取当前市场上所有股票的实时数据，通常需要几秒钟时间。
          </p>

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-sm text-blue-800 dark:text-blue-300">
              <strong>实时性说明：</strong>实时行情数据通常有 <strong>3-5 秒的延迟</strong>，非 Level-2 高频数据。
              适用于监控市场整体情况和快速筛选热门股票。
            </p>
          </div>

          <button
            onClick={handleSync}
            disabled={isLoading}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? '获取中...' : '立即获取实时行情'}
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
                <li>股票代码、名称</li>
                <li>最新价格</li>
                <li>涨跌额、涨跌幅</li>
                <li>今日开盘价、收盘价</li>
                <li>今日最高价、最低价</li>
                <li>成交量、成交额</li>
                <li>换手率、市盈率</li>
                <li>总市值、流通市值</li>
                <li>振幅、量比</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>市场整体监控</li>
                <li>热门股票筛选</li>
                <li>涨跌幅排行</li>
                <li>异动股票捕捉</li>
                <li>实时选股条件筛选</li>
                <li>盘中监控和提醒</li>
                <li>成交量异常分析</li>
                <li>资金流向监控</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 应用场景 */}
      <div className="card bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
        <h3 className="text-lg font-semibold text-purple-900 dark:text-purple-200 mb-3">
          🎯 典型应用场景
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-purple-800 dark:text-purple-300">
          <div>
            <strong>场景 1: 市场概览</strong>
            <p className="mt-1">快速了解当前市场的整体涨跌情况，识别市场热点板块和个股。</p>
          </div>
          <div>
            <strong>场景 2: 实时选股</strong>
            <p className="mt-1">根据涨跌幅、成交量、换手率等指标，实时筛选符合条件的股票。</p>
          </div>
          <div>
            <strong>场景 3: 异动监控</strong>
            <p className="mt-1">监控成交量放大、价格急涨急跌等异常情况，及时捕捉交易机会。</p>
          </div>
          <div>
            <strong>场景 4: 盘中提醒</strong>
            <p className="mt-1">设置价格或涨跌幅阈值，盘中自动监控并发送提醒通知。</p>
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
            <span>实时行情数据<strong>仅在交易时间段（9:30-15:00）有效</strong>，非交易时段显示前一交易日收盘数据</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据通常有 <strong>3-5 秒延迟</strong>，不适用于高频交易或精确的短线操作</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>实时行情数据<strong>暂未保存到数据库</strong>，当前版本仅用于实时查询和筛选</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>请勿<strong>频繁刷新</strong>（建议间隔至少 5-10 秒），避免触发 API 限流</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>部分数据源对<strong>实时行情接口有调用频率限制</strong>，请合理使用</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据源可在<a href="/settings" className="underline">系统设置</a>中切换（AkShare 或 Tushare）</span>
          </li>
        </ul>
      </div>

      {/* 交易时间提示 */}
      <div className="card bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
        <h3 className="text-lg font-semibold text-green-900 dark:text-green-200 mb-3">
          🕐 A股交易时间
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-green-800 dark:text-green-300">
          <div>
            <strong>上午交易时段（集合竞价）</strong>
            <p className="mt-1">09:15 - 09:25（集合竞价）</p>
            <p>09:25 - 09:30（集合竞价撮合）</p>
          </div>
          <div>
            <strong>上午交易时段（连续竞价）</strong>
            <p className="mt-1">09:30 - 11:30</p>
          </div>
          <div>
            <strong>下午交易时段（连续竞价）</strong>
            <p className="mt-1">13:00 - 15:00</p>
          </div>
          <div>
            <strong>尾盘集合竞价（深圳）</strong>
            <p className="mt-1">14:57 - 15:00</p>
          </div>
        </div>
        <p className="text-xs text-green-700 dark:text-green-400 mt-3">
          * 非交易时段获取的数据为前一交易日的收盘数据
        </p>
      </div>
    </div>
  )
}
