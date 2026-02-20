'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import AdminLayout from '@/components/layouts/AdminLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { apiClient } from '@/lib/api-client'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import {
  Activity,
  Database,
  TrendingUp,
  Clock,
  CheckCircle2
} from 'lucide-react'

interface SystemStats {
  stockCount: number
  syncStatus: string
  lastSyncTime: string
  todayTasks: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<SystemStats>({
    stockCount: 0,
    syncStatus: 'unknown',
    lastSyncTime: '-',
    todayTasks: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      // 获取系统状态
      const syncStatus = await apiClient.getSyncStatus()

      // 构建统计数据
      setStats({
        stockCount: syncStatus.data?.total || 0,
        syncStatus: syncStatus.data?.status === 'syncing' ? 'syncing' : 'idle',
        lastSyncTime: syncStatus.data?.last_sync_date || '-',
        todayTasks: 0
      })
    } catch (error) {
      console.error('加载统计数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute requireAdmin>
      <AdminLayout>
        <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            管理控制台
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            股票分析系统管理后台 - 系统监控与管理
          </p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* 系统状态 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                系统状态
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                {stats.syncStatus === 'syncing' ? (
                  <>
                    <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
                    <span className="text-2xl font-bold text-yellow-600">同步中</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="text-2xl font-bold text-green-600">运行中</span>
                  </>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                所有服务正常运行
              </p>
            </CardContent>
          </Card>

          {/* 股票数量 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                股票数量
              </CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse">
                  <div className="h-8 bg-gray-200 rounded w-20"></div>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.stockCount.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground mt-2">
                    已同步的A股数量
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {/* 最后同步时间 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                最后同步
              </CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.lastSyncTime === '-' ? '-' : new Date(stats.lastSyncTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {stats.lastSyncTime === '-' ? '暂无同步记录' : new Date(stats.lastSyncTime).toLocaleDateString('zh-CN')}
              </p>
            </CardContent>
          </Card>

          {/* 今日任务 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                今日任务
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.todayTasks}</div>
              <p className="text-xs text-muted-foreground mt-2">
                待执行的定时任务
              </p>
            </CardContent>
          </Card>
        </div>

        {/* 快捷操作 */}
        <Card>
          <CardHeader>
            <CardTitle>快捷操作</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link
                href="/settings"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <div className="font-medium">系统设置</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">配置数据源</div>
                </div>
              </Link>

              <Link
                href="/sync"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <Database className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <div className="font-medium">数据同步</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">同步股票数据</div>
                </div>
              </Link>

              <Link
                href="/monitor"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <div className="font-medium">性能监控</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">查看系统状态</div>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* 系统信息 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>系统信息</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">版本</dt>
                  <dd className="font-medium">v1.0.0</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">环境</dt>
                  <dd className="font-medium">生产环境</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">数据库</dt>
                  <dd className="font-medium">TimescaleDB</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">缓存</dt>
                  <dd className="font-medium">Redis</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>使用提示</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>首次使用请先在系统设置中配置数据源</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>然后在数据同步页面执行初始化同步</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>建议每日收盘后执行增量同步更新数据</span>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
      </AdminLayout>
    </ProtectedRoute>
  )
}
