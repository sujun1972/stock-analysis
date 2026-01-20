'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

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

export default function StockListSyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<ModuleSyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    loadSyncStatus()
    const interval = setInterval(() => {
      if (syncStatus?.status === 'running') {
        loadSyncStatus()
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [syncStatus?.status])

  const loadSyncStatus = async () => {
    try {
      const response = await apiClient.getModuleSyncStatus('stock_list')
      if (response.data) {
        setSyncStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load sync status:', err)
    }
  }

  const handleSync = async () => {
    setIsLoading(true)
    setError(null)
    setSuccessMessage(null)

    // 启动同步请求（不等待完成）
    apiClient.syncStockList()
      .then((response) => {
        if (response.data) {
          setSuccessMessage(`成功同步股票列表！共获取 ${response.data.total || 0} 只股票`)
          setTimeout(() => setSuccessMessage(null), 5000)
        }
        setIsLoading(false)
      })
      .catch((err: any) => {
        const errorMessage = err.response?.data?.detail || err.message || '同步股票列表失败'
        setError(errorMessage)
        console.error('Sync error:', err)
        setIsLoading(false)
      })

    // 立即开始轮询状态（每2秒一次）
    const pollInterval = setInterval(async () => {
      await loadSyncStatus()

      // 如果状态不是 running，停止轮询
      const status = syncStatus?.status
      if (status && status !== 'running') {
        clearInterval(pollInterval)
      }
    }, 2000)

    // 30秒后强制停止轮询（防止无限轮询）
    setTimeout(() => {
      clearInterval(pollInterval)
    }, 30000)
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
          📋 股票列表同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          从数据源获取最新的 A 股股票列表，包括股票代码、名称、行业、地区等基本信息
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

      {/* 当前状态 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          上次同步信息
        </h2>
        {syncStatus ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">状态</div>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(syncStatus.status)}`}>
                  {getStatusText(syncStatus.status)}
                </span>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">开始时间</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {syncStatus.started_at || '未同步'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成时间</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {syncStatus.completed_at || '-'}
                </div>
              </div>
            </div>

            {syncStatus.status === 'completed' && syncStatus.success > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">同步总数</div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {syncStatus.total || 0} 只
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">成功</div>
                  <div className="font-medium text-green-600 dark:text-green-400">
                    {syncStatus.success || 0} 只
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">失败</div>
                  <div className="font-medium text-red-600 dark:text-red-400">
                    {syncStatus.failed || 0} 只
                  </div>
                </div>
              </div>
            )}

            {syncStatus.error_message && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <div className="text-sm font-medium text-red-900 dark:text-red-200 mb-1">错误详情：</div>
                <div className="text-sm text-red-800 dark:text-red-300 whitespace-pre-wrap">
                  {syncStatus.error_message}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-600 dark:text-gray-400">加载状态中...</div>
        )}
      </div>

      {/* 同步操作 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          开始同步
        </h2>
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            点击下方按钮从当前配置的数据源获取最新的股票列表。同步时间取决于数据源速度，通常需要几秒到几分钟。
          </p>
          <button
            onClick={handleSync}
            disabled={isLoading || syncStatus?.status === 'running'}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading || syncStatus?.status === 'running' ? '同步中...' : '开始同步股票列表'}
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
                <li>股票代码（如 000001）</li>
                <li>股票名称（如 平安银行）</li>
                <li>市场类型（上海/深圳主板等）</li>
                <li>所属行业</li>
                <li>所属地区</li>
                <li>上市日期</li>
                <li>状态（正常/退市等）</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>股票基础信息查询</li>
                <li>行业、地区筛选</li>
                <li>股票池构建</li>
                <li>后续数据同步的基础</li>
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
            <span>股票列表数据通常比较稳定，建议<strong>每月更新一次</strong>即可</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>同步会<strong>覆盖更新</strong>现有数据，保持数据最新</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>不同数据源（AkShare/Tushare）可能获取的股票数量略有差异</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>请确保在<a href="/settings" className="underline">系统设置</a>中正确配置了数据源</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
