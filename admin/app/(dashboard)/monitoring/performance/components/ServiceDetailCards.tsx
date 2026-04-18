'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Database, Zap } from 'lucide-react'
import { type HealthStatus, getServiceStatus } from '../hooks/useMonitorData'
import { StatusBadge } from './StatusBadge'

interface ServiceDetailCardsProps {
  health: HealthStatus | null
}

export const ServiceDetailCards = ({ health }: ServiceDetailCardsProps) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 数据库状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            数据库状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">连接状态</span>
              <StatusBadge status={getServiceStatus(health?.checks?.database).status} />
            </div>

            {health?.checks?.database?.response_time_ms && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">响应时间</span>
                  <span className="font-semibold">{health.checks.database.response_time_ms}ms</span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">性能</span>
                    <span className="text-xs">
                      {health.checks.database.response_time_ms < 50
                        ? '优秀'
                        : health.checks.database.response_time_ms < 100
                        ? '良好'
                        : '需优化'}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(100, (health.checks.database.response_time_ms / 200) * 100)}
                    className="h-2"
                  />
                </div>
              </>
            )}

            {health?.checks?.database?.message && (
              <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                {health.checks.database.message}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Redis状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Redis缓存
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">连接状态</span>
              <StatusBadge status={getServiceStatus(health?.checks?.redis).status} />
            </div>

            {health?.checks?.redis?.ping_time_ms && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Ping延迟</span>
                  <span className="font-semibold">{health.checks.redis.ping_time_ms}ms</span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">性能</span>
                    <span className="text-xs">
                      {health.checks.redis.ping_time_ms < 10
                        ? '优秀'
                        : health.checks.redis.ping_time_ms < 50
                        ? '良好'
                        : '需优化'}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(100, (health.checks.redis.ping_time_ms / 100) * 100)}
                    className="h-2"
                  />
                </div>
              </>
            )}

            {health?.checks?.redis?.message && (
              <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                {health.checks.redis.message}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
