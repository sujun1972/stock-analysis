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

interface DataSourceConfig {
  data_source: string
  tushare_token: string
}

export default function SyncOverviewPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [dataSource, setDataSource] = useState<DataSourceConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statusRes, configRes] = await Promise.all([
        apiClient.getSyncStatus(),
        apiClient.getDataSourceConfig()
      ])
      if (statusRes.data) {
        setSyncStatus(statusRes.data)
      }
      if (configRes.data) {
        setDataSource(configRes.data)
      }
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const syncModules = [
    {
      id: 'stock-list',
      title: '股票列表同步',
      description: '获取并更新 A 股市场所有股票的基本信息（约 5000+ 只）',
      icon: '📋',
      path: '/sync/stock-list',
      color: 'blue'
    },
    {
      id: 'new-stocks',
      title: '新股列表同步',
      description: '获取最近上市的新股信息，支持增量更新，建议每日同步',
      icon: '🆕',
      path: '/sync/new-stocks',
      color: 'cyan'
    },
    {
      id: 'delisted-stocks',
      title: '退市列表同步',
      description: '获取已退市股票信息，更新股票状态，建议每周同步',
      icon: '📉',
      path: '/sync/delisted-stocks',
      color: 'red'
    },
    {
      id: 'daily',
      title: '日线数据同步',
      description: '批量同步股票的历史日线数据（OHLCV），支持选择时间范围和股票数量',
      icon: '📊',
      path: '/sync/daily',
      color: 'green'
    },
    {
      id: 'realtime',
      title: '实时行情同步',
      description: '获取最新的实时行情快照，包括当前价格、涨跌幅等信息',
      icon: '⚡',
      path: '/sync/realtime',
      color: 'yellow'
    }
  ]

  // 分时数据已改为按需加载，在股票分析页面自动获取

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
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          数据同步管理
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          管理股票数据的获取和更新，当前数据源: <span className="font-medium text-blue-600 dark:text-blue-400">{dataSource?.data_source || '加载中...'}</span>
        </p>
      </div>

      {/* 当前同步状态卡片 */}
      <div className="card">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            当前同步状态
          </h2>
          <button
            onClick={loadData}
            disabled={loading}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
          >
            {loading ? '刷新中...' : '刷新状态'}
          </button>
        </div>

        {loading ? (
          <div className="text-center py-4 text-gray-600 dark:text-gray-400">
            加载状态中...
          </div>
        ) : syncStatus ? (
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
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${syncStatus.progress}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-4 text-red-600 dark:text-red-400">
            无法加载同步状态
          </div>
        )}
      </div>

      {/* 同步模块卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {syncModules.map((module) => (
          <div
            key={module.id}
            className="card hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => router.push(module.path)}
          >
            <div className="flex items-start space-x-4">
              <div className="text-4xl">{module.icon}</div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {module.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {module.description}
                </p>
                <button className="btn-secondary text-sm">
                  进入同步 →
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 使用提示 */}
      <div className="card bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-200 mb-3">
          💡 使用建议
        </h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-300">
          <li className="flex items-start">
            <span className="mr-2">1.</span>
            <span>首次使用请先同步<strong>股票列表</strong>，建立股票基础数据</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">2.</span>
            <span>然后根据需要同步<strong>日线数据</strong>，建议从少量股票开始测试</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">3.</span>
            <span><strong>分时数据</strong>和<strong>实时行情</strong>适用于短期交易分析</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">4.</span>
            <span>数据源设置可在<a href="/settings" className="underline">系统设置</a>中切换（AkShare 或 Tushare）</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">5.</span>
            <span>注意 API 限流：AkShare 有 IP 限制，Tushare 有积分和频率限制</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
