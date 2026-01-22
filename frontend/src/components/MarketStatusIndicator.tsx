'use client'

import { useMarketStatus } from '@/hooks/useMarketStatus'
import { Badge } from '@/components/ui/badge'
import { Clock, TrendingUp, Moon, Sun } from 'lucide-react'

/**
 * 市场状态指示器组件
 * 显示当前市场状态和下一个交易时段
 */
export function MarketStatusIndicator() {
  const { marketStatus, loading } = useMarketStatus()

  if (loading || !marketStatus) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Clock className="w-4 h-4 animate-spin" />
        <span>加载中...</span>
      </div>
    )
  }

  // 根据市场状态选择图标和颜色
  const getStatusIcon = () => {
    switch (marketStatus.status) {
      case 'trading':
        return <TrendingUp className="w-4 h-4" />
      case 'call_auction':
        return <Clock className="w-4 h-4" />
      case 'closed':
      case 'after_hours':
      case 'pre_market':
        return <Moon className="w-4 h-4" />
      default:
        return <Sun className="w-4 h-4" />
    }
  }

  const getStatusColor = () => {
    switch (marketStatus.status) {
      case 'trading':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'call_auction':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      case 'closed':
      case 'after_hours':
      case 'pre_market':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
      default:
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Badge className={`flex items-center gap-1.5 px-3 py-1 ${getStatusColor()}`}>
        {getStatusIcon()}
        <span>{marketStatus.description}</span>
      </Badge>

      {marketStatus.next_session_time && !marketStatus.is_trading && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {marketStatus.next_session_desc}: {new Date(marketStatus.next_session_time).toLocaleString('zh-CN', {
            month: 'numeric',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </span>
      )}
    </div>
  )
}
