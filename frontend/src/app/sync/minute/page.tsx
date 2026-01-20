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

export default function MinuteSyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // 同步参数
  const [stockCode, setStockCode] = useState<string>('')
  const [period, setPeriod] = useState<string>('5')
  const [days, setDays] = useState<number>(5)

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
    if (!stockCode.trim()) {
      setError('请输入股票代码')
      return
    }

    try {
      setIsLoading(true)
      setError(null)
      setSuccessMessage(null)

      const response = await apiClient.syncMinuteData(stockCode, {
        period,
        days
      })

      if (response.data) {
        const { code, records } = response.data
        setSuccessMessage(`成功同步 ${code} 的 ${period} 分钟数据！共 ${records} 条记录`)
      }

      await loadSyncStatus()
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '同步分时数据失败'
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
          ⏱️ 分时数据同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          同步股票的分钟级历史数据（1/5/15/30/60 分钟 K 线），适用于短期交易和日内分析
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 股票代码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                股票代码
              </label>
              <input
                type="text"
                value={stockCode}
                onChange={(e) => setStockCode(e.target.value)}
                placeholder="例如: 000001"
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                输入 6 位股票代码（不含前缀）
              </p>
            </div>

            {/* 分时周期 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                分时周期
              </label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value="1">1 分钟</option>
                <option value="5">5 分钟（推荐）</option>
                <option value="15">15 分钟</option>
                <option value="30">30 分钟</option>
                <option value="60">60 分钟</option>
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                周期越小，数据量越大
              </p>
            </div>

            {/* 历史天数 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                历史天数
              </label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                disabled={isLoading}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value={1}>1 天</option>
                <option value={5}>5 天（推荐）</option>
                <option value={10}>10 天</option>
                <option value={30}>30 天</option>
                <option value={60}>60 天</option>
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                部分数据源有历史数据限制
              </p>
            </div>
          </div>

          {/* 开始同步按钮 */}
          <button
            onClick={handleSync}
            disabled={isLoading || !stockCode.trim()}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? '同步中...' : '开始同步'}
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
                <li>分时时间戳</li>
                <li>开盘价、收盘价</li>
                <li>最高价、最低价</li>
                <li>成交量、成交额</li>
                <li>周期内涨跌幅</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>日内交易策略</li>
                <li>短线分析</li>
                <li>波段捕捉</li>
                <li>分时形态识别</li>
                <li>高频交易回测</li>
                <li>分时指标计算</li>
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
            <span>分时数据<strong>目前仅支持单只股票同步</strong>，批量同步功能后续版本提供</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>部分数据源对<strong>分时数据的历史范围有限制</strong>（如仅提供最近 30-60 天）</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>1 分钟级别数据量较大，建议优先使用 <strong>5 分钟或更长周期</strong></span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>分时数据<strong>暂未保存到数据库</strong>，当前版本仅用于测试和验证</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>请注意 <strong>API 限流</strong>，避免频繁请求导致封禁</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据源可在<a href="/settings" className="underline">系统设置</a>中切换（AkShare 或 Tushare）</span>
          </li>
        </ul>
      </div>

      {/* 快速参考 */}
      <div className="card bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-200 mb-3">
          💡 常用股票代码参考
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-blue-800 dark:text-blue-300">
          <div><strong>000001</strong> - 平安银行</div>
          <div><strong>000002</strong> - 万科A</div>
          <div><strong>600000</strong> - 浦发银行</div>
          <div><strong>600519</strong> - 贵州茅台</div>
          <div><strong>000858</strong> - 五粮液</div>
          <div><strong>601318</strong> - 中国平安</div>
          <div><strong>600036</strong> - 招商银行</div>
          <div><strong>000333</strong> - 美的集团</div>
        </div>
      </div>
    </div>
  )
}
