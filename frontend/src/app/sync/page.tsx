'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

interface DataSourceConfig {
  data_source: string
  tushare_token: string
}

export default function SyncOverviewPage() {
  const router = useRouter()
  const [dataSource, setDataSource] = useState<DataSourceConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const configRes = await apiClient.getDataSourceConfig()
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
      id: 'initialize',
      title: '数据初始化',
      description: '首次使用时执行：同步股票列表和历史日线数据，建立完整的数据基础',
      icon: '🚀',
      path: '/sync/initialize',
      color: 'indigo'
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
      id: 'realtime',
      title: '实时行情同步',
      description: '获取最新的实时行情快照，包括当前价格、涨跌幅等信息',
      icon: '⚡',
      path: '/sync/realtime',
      color: 'yellow'
    }
  ]

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
            <span>首次使用请先执行<strong>数据初始化</strong>，按步骤完成股票列表和日线数据同步</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">2.</span>
            <span>完成初始化后，可使用<strong>增量同步</strong>功能定期更新新股、退市和实时行情数据</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">3.</span>
            <span><strong>实时行情</strong>适用于盘中交易分析，<strong>分时数据</strong>在股票详情页按需加载</span>
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
