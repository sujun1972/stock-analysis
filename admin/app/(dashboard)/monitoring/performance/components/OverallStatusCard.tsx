'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Database, Server, Cpu, Zap } from 'lucide-react'
import { type HealthStatus, getServiceStatus } from '../hooks/useMonitorData'
import { StatusBadge } from './StatusBadge'

interface OverallStatusCardProps {
  health: HealthStatus | null
  overallStatus: string
  error: string | null
}

export const OverallStatusCard = ({ health, overallStatus, error }: OverallStatusCardProps) => {
  return (
    <Card className={`border-2 ${
      overallStatus === 'healthy'
        ? 'border-green-500 bg-green-50 dark:bg-green-900/10'
        : overallStatus === 'degraded'
        ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/10'
        : 'border-red-500 bg-red-50 dark:bg-red-900/10'
    }`}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <CardTitle className="text-xl sm:text-2xl flex items-center gap-3">
            <Server className="h-6 w-6 sm:h-8 sm:w-8" />
            系统总体状态
          </CardTitle>
          <StatusBadge status={overallStatus} />
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="text-red-600 dark:text-red-400">{error}</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div className="flex items-center gap-3 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg">
              <Database className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">数据库</div>
                <div className="font-semibold truncate">
                  {getServiceStatus(health?.checks?.database).status === 'healthy' ? '正常' : '异常'}
                </div>
                {getServiceStatus(health?.checks?.database).responseTime && (
                  <div className="text-xs text-gray-500">
                    {getServiceStatus(health?.checks?.database).responseTime}ms
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg">
              <Zap className="h-6 w-6 sm:h-8 sm:w-8 text-red-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">Redis</div>
                <div className="font-semibold truncate">
                  {getServiceStatus(health?.checks?.redis).status === 'healthy' ? '正常' : '异常'}
                </div>
                {getServiceStatus(health?.checks?.redis).responseTime && (
                  <div className="text-xs text-gray-500">
                    {getServiceStatus(health?.checks?.redis).responseTime}ms
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg">
              <Cpu className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">核心服务</div>
                <div className="font-semibold truncate">
                  {getServiceStatus(health?.checks?.core_service).status === 'healthy' ? '正常' : '异常'}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg">
              <Activity className="h-6 w-6 sm:h-8 sm:w-8 text-green-600 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">熔断器</div>
                <div className="font-semibold truncate">
                  {health?.checks?.circuit_breakers?.status || '未知'}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
