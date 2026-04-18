'use client'

import Link from 'next/link'
import {
  RefreshCw, Database, XCircle, Loader2, RotateCcw, Zap, Settings, Clock, Play
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTaskStore } from '@/stores/task-store'
import type { SyncOverviewItem } from '@/lib/api/sync-dashboard'

import { StatusDot } from './StatusDot'
import { STRATEGY_LABELS } from './constants'
import { formatDuration, formatDate } from '../hooks/utils'

export function SyncRow({
  item,
  onSync,
  onClearProgress,
  onEdit,
  onTest,
}: {
  item: SyncOverviewItem
  onSync: (item: SyncOverviewItem, type: 'incremental' | 'full') => void
  onClearProgress: (item: SyncOverviewItem) => void
  onEdit: (item: SyncOverviewItem) => void
  onTest: (item: SyncOverviewItem) => void
}) {
  const isTaskRunning = useTaskStore(state => state.isTaskRunning)
  const incTask = item.last_incremental
  const fullTask = item.last_full_sync
  const progress = item.redis_progress
  const hasFullSync = !!item.full_sync_task_name
  // 增量和全量共用同一任务（基础数据类），没有独立全量路由
  const isSharedTask = hasFullSync && item.full_sync_task_name === item.incremental_task_name
  const isIncrSyncing = item.incremental_task_name ? isTaskRunning(item.incremental_task_name) : false
  const isFullSyncing = item.full_sync_task_name ? isTaskRunning(item.full_sync_task_name) : false

  return (
    <div className="grid grid-cols-12 gap-2 items-center py-2.5 px-3 border-b border-gray-100 hover:bg-gray-50 text-sm">
      {/* 名称 */}
      <div className="col-span-3 min-w-0">
        <div className="flex items-center gap-1.5">
          {item.page_url ? (
            <Link href={item.page_url} className="font-medium text-blue-600 hover:underline truncate">
              {item.display_name}
            </Link>
          ) : (
            <span className="font-medium truncate">{item.display_name}</span>
          )}
          {item.passive_sync_enabled && (
            <Zap className="w-3 h-3 text-yellow-500 flex-shrink-0" aria-label="已启用被动同步" />
          )}
        </div>
        {item.last_data_date && (
          <div className="text-xs text-gray-400 mt-0.5">
            数据至 {item.last_data_date.replace(/^(\d{4})(\d{2})(\d{2})$/, '$1-$2-$3')}
          </div>
        )}
      </div>

      {/* 增量同步状态 */}
      <div className="col-span-3 min-w-0">
        <div className="flex items-center gap-1.5">
          <StatusDot status={incTask?.status} />
          <span className="text-gray-500 text-xs truncate">
            {incTask ? formatDate(incTask.completed_at || incTask.started_at) : '从未同步'}
            {incTask?.duration_ms && (
              <span className="ml-1 text-gray-400">({formatDuration(incTask.duration_ms)})</span>
            )}
          </span>
          {incTask?.status === 'failure' && (
            <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" aria-label={incTask.error || '未知错误'} />
          )}
        </div>
        {item.incremental_schedule?.enabled && item.incremental_schedule.cron_expression && (
          <div className="flex items-center gap-1 mt-0.5">
            <Clock className="w-3 h-3 text-blue-400 flex-shrink-0" />
            <span className="text-[11px] text-blue-500 font-mono">{item.incremental_schedule.cron_expression}</span>
          </div>
        )}
      </div>

      {/* 全量同步状态 */}
      <div className="col-span-2 flex items-center gap-1.5 min-w-0">
        {hasFullSync ? (
          <>
            <StatusDot status={isSharedTask ? incTask?.status : fullTask?.status} />
            <span className="text-gray-500 text-xs truncate" title={isSharedTask ? '共用增量任务，以最早日期为起点全量同步' : undefined}>
              {isSharedTask
                ? (incTask ? formatDate(incTask.completed_at || incTask.started_at) : '从未同步')
                : (fullTask ? formatDate(fullTask.completed_at || fullTask.started_at) : '从未同步')
              }
            </span>
            {!isSharedTask && progress && (
              <Badge
                variant="outline"
                className="text-xs py-0 px-1 text-orange-600 border-orange-300 cursor-default"
                title={`Redis中有 ${progress.completed_count} 条进度记录，下次全量同步将续继`}
              >
                续继 {progress.completed_count}
              </Badge>
            )}
          </>
        ) : (
          <span className="text-gray-400 text-xs">
            {item.full_sync_strategy === 'snapshot' ? '快照' : '-'}
          </span>
        )}
      </div>

      {/* 策略 + 接口参数 */}
      <div className="col-span-2 text-xs text-gray-400">
        {item.full_sync_strategy && item.full_sync_strategy !== 'none'
          ? STRATEGY_LABELS[item.full_sync_strategy] : ''}
        {item.api_name ? (
          <div className="text-gray-300 truncate" title={item.api_name}>{item.api_name}</div>
        ) : null}
        {item.api_params && (
          <div className="flex flex-wrap gap-0.5 mt-0.5">
            {item.api_params.ts_code !== 'none' && (
              <span className={`px-1 rounded text-[10px] ${
                item.api_params.ts_code === 'required' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
              }`} title={item.api_params.ts_code === 'required' ? 'ts_code 必填或至少传一个' : 'ts_code 可选'}>
                code{item.api_params.ts_code === 'required' ? '*' : ''}
              </span>
            )}
            {item.api_params.trade_date !== 'none' && (
              <span className={`px-1 rounded text-[10px] ${
                item.api_params.trade_date === 'required' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
              }`} title={item.api_params.trade_date === 'required' ? 'trade_date 必填' : 'trade_date 可选'}>
                日期{item.api_params.trade_date === 'required' ? '*' : ''}
              </span>
            )}
            {item.api_params.start_date && (
              <span className="px-1 rounded text-[10px] bg-green-50 text-green-600" title="支持 start_date/end_date 日期范围查询">
                范围
              </span>
            )}
            {item.api_params.special_params?.month && (
              <span className="px-1 rounded text-[10px] bg-purple-100 text-purple-600" title="month 必填 (YYYYMM)">
                月*
              </span>
            )}
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="col-span-2 flex items-center justify-end gap-1">
        {item.incremental_task_name && (
          <Button size="sm" variant="outline" className="h-6 px-2 text-xs"
            disabled={isIncrSyncing} onClick={() => onSync(item, 'incremental')}>
            {isIncrSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            <span className="ml-1 hidden lg:inline">增量</span>
          </Button>
        )}
        {hasFullSync && (
          <Button size="sm" variant="outline"
            className="h-6 px-2 text-xs border-orange-200 text-orange-700 hover:bg-orange-50"
            disabled={isFullSyncing} onClick={() => onSync(item, 'full')}>
            {isFullSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3" />}
            <span className="ml-1 hidden lg:inline">全量</span>
          </Button>
        )}
        {progress && (
          <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-red-500"
            onClick={() => onClearProgress(item)}>
            <RotateCcw className="w-3 h-3" />
          </Button>
        )}
        {item.api_name && (
          <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-green-600"
            title="测试接口" onClick={() => onTest(item)}>
            <Play className="w-3 h-3" />
          </Button>
        )}
        <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-blue-600"
          onClick={() => onEdit(item)}>
          <Settings className="w-3 h-3" />
        </Button>
      </div>
    </div>
  )
}
