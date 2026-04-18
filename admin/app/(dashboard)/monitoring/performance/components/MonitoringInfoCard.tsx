'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Activity } from 'lucide-react'

export const MonitoringInfoCard = () => {
  return (
    <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border-blue-200 dark:border-blue-800">
      <CardContent className="pt-4 sm:pt-6">
        <div className="flex items-start gap-3">
          <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-3 text-base sm:text-lg">
              监控架构说明
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              <div>
                <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2 text-xs sm:text-sm">
                  健康检查（本页面）
                </h4>
                <ul className="text-xs sm:text-sm text-blue-700 dark:text-blue-400 space-y-1 sm:space-y-1.5">
                  <li>• 自动每 10 秒刷新服务状态</li>
                  <li>• 监控数据库、Redis、核心服务</li>
                  <li>• 显示响应时间和连接状态</li>
                  <li>• 适合快速巡检和故障排查</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2 text-xs sm:text-sm">
                  性能指标（Grafana）
                </h4>
                <ul className="text-xs sm:text-sm text-blue-700 dark:text-blue-400 space-y-1 sm:space-y-1.5">
                  <li>• 图表自动每 10 秒刷新数据</li>
                  <li>• 显示请求量、响应时间、错误率</li>
                  <li>• 支持自定义时间范围查询</li>
                  <li>• 适合性能分析和容量规划</li>
                </ul>
              </div>
            </div>
            <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-blue-200 dark:border-blue-800">
              <p className="text-xs sm:text-sm text-blue-700 dark:text-blue-400 break-all">
                <strong>访问地址：</strong><br className="sm:hidden" />
                <span className="inline-block mt-1 sm:mt-0 sm:ml-2">
                  Grafana: <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 rounded text-xs">http://localhost:3001</code>
                  <span className="text-xs ml-1">（admin / admin123）</span>
                </span>
                <br className="sm:hidden" />
                <span className="inline-block mt-1 sm:mt-0 sm:ml-2">
                  Prometheus: <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 rounded text-xs">http://localhost:9090</code>
                </span>
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
