'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  Globe,
  CreditCard,
  DollarSign,
  RefreshCw,
  CheckCircle,
  Clock,
  XCircle
} from 'lucide-react'

interface SyncStatus {
  module: string
  title: string
  points: number
  lastSync: string | null
  status: 'success' | 'running' | 'pending' | 'failed'
  records: number
  nextRun: string | null
  error?: string
}

interface PointsStats {
  dailyConsumed: number
  monthlyConsumed: number
  remainingQuota: number
  totalQuota: number
}

// 同步状态卡片组件
function SyncStatusCard({
  title,
  module,
  points,
  lastSync,
  status,
  records,
  warning
}: SyncStatus & { warning?: string }) {
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'running':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
      case 'pending':
        return <Clock className="h-5 w-5 text-gray-400" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'running':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'pending':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {getStatusIcon()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">模块</span>
            <Badge variant="outline" className="text-xs">{module}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">积分消耗</span>
            <span className={`text-xs font-medium ${points >= 1000 ? 'text-red-600' : 'text-yellow-600'}`}>
              {points} 积分
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">状态</span>
            <Badge className={`text-xs ${getStatusColor()}`}>
              {status === 'success' ? '成功' :
               status === 'running' ? '运行中' :
               status === 'pending' ? '待执行' : '失败'}
            </Badge>
          </div>
          {lastSync && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">上次同步</span>
              <span className="text-xs">{lastSync}</span>
            </div>
          )}
          {records > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">记录数</span>
              <span className="text-xs font-medium">{records.toLocaleString()}</span>
            </div>
          )}
          {warning && (
            <Alert className="mt-2">
              <AlertTriangle className="h-3 w-3" />
              <AlertDescription className="text-xs">{warning}</AlertDescription>
            </Alert>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function ExtendedSyncMonitor() {
  const [syncStatuses, setSyncStatuses] = useState<SyncStatus[]>([])
  const [pointsStats, setPointsStats] = useState<PointsStats>({
    dailyConsumed: 0,
    monthlyConsumed: 0,
    remainingQuota: 50000,
    totalQuota: 50000
  })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadSyncStatuses()
    loadPointsStats()
    // 每30秒自动刷新
    const interval = setInterval(() => {
      loadSyncStatuses()
      loadPointsStats()
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadSyncStatuses = async () => {
    try {
      // 模拟数据，实际应调用API
      const statuses: SyncStatus[] = [
        {
          module: 'extended.sync_daily_basic',
          title: '每日指标',
          points: 120,
          lastSync: '2024-03-17 17:00',
          status: 'success',
          records: 4850,
          nextRun: '2024-03-18 17:00'
        },
        {
          module: 'extended.sync_moneyflow',
          title: '资金流向',
          points: 2000,
          lastSync: '2024-03-17 17:30',
          status: 'running',
          records: 100,
          nextRun: '2024-03-18 17:30'
        },
        {
          module: 'extended.sync_hk_hold',
          title: '北向资金',
          points: 300,
          lastSync: null,
          status: 'pending',
          records: 0,
          nextRun: '2024-03-17 18:00'
        },
        {
          module: 'extended.sync_margin',
          title: '融资融券',
          points: 300,
          lastSync: '2024-03-17 18:30',
          status: 'success',
          records: 3200,
          nextRun: '2024-03-18 18:30'
        },
        {
          module: 'extended.sync_stk_limit',
          title: '涨跌停价格',
          points: 120,
          lastSync: '2024-03-17 09:00',
          status: 'success',
          records: 4850,
          nextRun: '2024-03-18 09:00'
        },
        {
          module: 'extended.sync_block_trade',
          title: '大宗交易',
          points: 300,
          lastSync: null,
          status: 'pending',
          records: 0,
          nextRun: '2024-03-17 19:00'
        }
      ]
      setSyncStatuses(statuses)
    } catch (error) {
      console.error('加载同步状态失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadPointsStats = async () => {
    try {
      // 模拟数据，实际应调用API
      setPointsStats({
        dailyConsumed: 1240,
        monthlyConsumed: 28560,
        remainingQuota: 21440,
        totalQuota: 50000
      })
    } catch (error) {
      console.error('加载积分统计失败:', error)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadSyncStatuses()
    await loadPointsStats()
    setRefreshing(false)
  }

  const handleManualSync = async (module: string) => {
    try {
      await apiClient.post(`/api/v1/extended/sync/trigger`, {
        data_type: module.replace('extended.sync_', '')
      })
      // 刷新状态
      await loadSyncStatuses()
    } catch (error) {
      console.error('触发同步失败:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="扩展数据同步监控"
        description="实时监控短线交易数据同步状态"
        actions={
          <Button onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        }
      />

      {/* 积分消耗统计 */}
      <Card>
        <CardHeader>
          <CardTitle>积分消耗统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span>今日已消耗</span>
              <span className="font-semibold">{pointsStats.dailyConsumed.toLocaleString()} 积分</span>
            </div>
            <div className="flex justify-between">
              <span>本月累计</span>
              <span className="font-semibold">{pointsStats.monthlyConsumed.toLocaleString()} 积分</span>
            </div>
            <div className="flex justify-between">
              <span>剩余配额</span>
              <span className="font-semibold text-green-600">
                {pointsStats.remainingQuota.toLocaleString()} 积分
              </span>
            </div>
            <Progress
              value={(pointsStats.monthlyConsumed / pointsStats.totalQuota) * 100}
              className="h-2"
            />
            <p className="text-xs text-gray-600 dark:text-gray-400">
              已使用 {((pointsStats.monthlyConsumed / pointsStats.totalQuota) * 100).toFixed(1)}% 的月度配额
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 同步状态卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {syncStatuses.map((status) => (
          <SyncStatusCard
            key={status.module}
            {...status}
            warning={status.points >= 2000 ? '高积分消耗' : undefined}
          />
        ))}
      </div>

      {/* 操作提示 */}
      <Alert>
        <Activity className="h-4 w-4" />
        <AlertDescription>
          <p className="font-semibold mb-2">同步说明</p>
          <ul className="text-xs space-y-1 list-disc list-inside">
            <li>每日指标、涨跌停价格建议每日同步</li>
            <li>资金流向数据消耗2000积分，建议谨慎使用</li>
            <li>北向资金、融资融券为重要参考指标，建议开启</li>
            <li>可在定时任务管理页面调整同步时间和频率</li>
          </ul>
        </AlertDescription>
      </Alert>
    </div>
  )
}