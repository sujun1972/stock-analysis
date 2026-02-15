'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import AdminLayout from '@/components/layouts/AdminLayout'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

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

interface ScheduledTask {
  id: number
  task_name: string
  module: string
  description: string
  cron_expression: string
  enabled: boolean
  params: any
}

export default function DelistedStocksSyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<ModuleSyncStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [scheduledTask, setScheduledTask] = useState<ScheduledTask | null>(null)

  useEffect(() => {
    loadSyncStatus()
    loadScheduledTask()
    const interval = setInterval(() => {
      if (syncStatus?.status === 'running') {
        loadSyncStatus()
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [syncStatus?.status])

  const loadSyncStatus = async () => {
    try {
      const response = await apiClient.getModuleSyncStatus('delisted_stocks')
      if (response.data) {
        setSyncStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load sync status:', err)
    }
  }

  const loadScheduledTask = async () => {
    try {
      const response = await apiClient.getScheduledTasks()
      if (response.data) {
        const task = response.data.find(t => t.task_name === 'weekly_delisted_stocks_sync')
        setScheduledTask(task || null)
      }
    } catch (err) {
      console.error('Failed to load scheduled task:', err)
    }
  }

  const handleToggleTask = async () => {
    if (!scheduledTask) return
    try {
      await apiClient.toggleScheduledTask(scheduledTask.id)
      await loadScheduledTask()
    } catch (err: any) {
      setError(err.message || '切换定时任务失败')
    }
  }

  const handleSync = async () => {
    setIsLoading(true)
    setError(null)
    setSuccessMessage(null)

    // 启动同步请求（不等待完成）
    apiClient.syncDelistedStocks()
      .then((response) => {
        if (response.data) {
          setSuccessMessage(`成功同步退市列表！共更新 ${response.data.total || 0} 只退市股票`)
          setTimeout(() => setSuccessMessage(null), 5000)
        }
        setIsLoading(false)
      })
      .catch((err: any) => {
        const errorMessage = err.response?.data?.detail || err.message || '同步退市列表失败'
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
    <ProtectedRoute requireAdmin>
      <AdminLayout>
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
          退市列表同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          获取已退市股票信息，更新股票状态和退市日期。建议每周同步以保持数据准确。
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
      <Card>
        <CardHeader>
          <CardTitle>上次同步信息</CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>

      {/* 定时任务配置 */}
      <Card className="bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800">
        <CardHeader>
          <CardTitle>定时任务配置</CardTitle>
        </CardHeader>
        <CardContent>
        {scheduledTask ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">任务描述</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {scheduledTask.description}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">执行计划</div>
                <code className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 px-2 py-1 rounded">
                  {scheduledTask.cron_expression}
                </code>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                启用自动同步：系统将按照 Cron 表达式自动执行同步任务
              </div>
              <button
                onClick={handleToggleTask}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  scheduledTask.enabled
                    ? 'bg-purple-600'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    scheduledTask.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              更多定时任务配置请访问 <a href="/settings/scheduler" className="text-purple-600 dark:text-purple-400 hover:underline">系统设置 - 定时任务</a>
            </div>
          </div>
        ) : (
          <div className="text-gray-600 dark:text-gray-400">加载定时任务配置中...</div>
        )}
        </CardContent>
      </Card>

      {/* 同步操作 */}
      <Card>
        <CardHeader>
          <CardTitle>开始同步</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            点击下方按钮从数据源获取退市股票列表。系统会自动更新对应股票的状态为&ldquo;退市&rdquo;并记录退市日期。
          </p>
          <button
            onClick={handleSync}
            disabled={isLoading || syncStatus?.status === 'running'}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading || syncStatus?.status === 'running' ? '同步中...' : '开始同步退市列表'}
          </button>
        </div>
        </CardContent>
      </Card>

      {/* 数据说明 */}
      <Card className="bg-gray-50 dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-lg">数据说明</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <strong>数据内容：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>退市股票代码和名称</li>
                <li>上市日期</li>
                <li>退市日期（暂停上市日期）</li>
                <li>退市原因（如适用）</li>
                <li>市场信息</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>自动更新股票状态</li>
                <li>风险预警和防范</li>
                <li>历史数据归档</li>
                <li>投资组合清理</li>
              </ul>
            </div>
          </div>
        </div>
        </CardContent>
      </Card>

      {/* 注意事项 */}
      <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
        <CardHeader>
          <CardTitle className="text-lg text-yellow-900 dark:text-yellow-200">注意事项</CardTitle>
        </CardHeader>
        <CardContent>
        <ul className="space-y-2 text-sm text-yellow-800 dark:text-yellow-300">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>建议<strong>每周同步一次</strong>，退市事件相对较少，无需频繁更新</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>同步会<strong>自动更新</strong>股票基础表中对应股票的状态和退市日期</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>退市股票的历史数据会<strong>保留</strong>，仅状态更新为&ldquo;退市&rdquo;</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>不同数据源（上交所/深交所）的退市信息会合并处理</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>可在<a href="/settings" className="underline">系统设置</a>中配置定时任务自动执行</span>
          </li>
          </ul>
        </CardContent>
      </Card>
      </div>
      </AdminLayout>
    </ProtectedRoute>
  )
}
