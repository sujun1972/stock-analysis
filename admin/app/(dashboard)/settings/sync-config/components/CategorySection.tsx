'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { SyncOverviewItem } from '@/lib/api/sync-dashboard'

import { SyncRow } from './SyncRow'

export function CategorySection({
  category, items, onSync, onClearProgress, onEdit, onTest,
}: {
  category: string
  items: SyncOverviewItem[]
  onSync: (item: SyncOverviewItem, type: 'incremental' | 'full') => void
  onClearProgress: (item: SyncOverviewItem) => void
  onEdit: (item: SyncOverviewItem) => void
  onTest: (item: SyncOverviewItem) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const failureCount = items.filter(
    i => i.last_incremental?.status === 'failure' || i.last_full_sync?.status === 'failure'
  ).length
  const progressCount = items.filter(i => i.redis_progress).length

  return (
    <Card className="overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          {expanded
            ? <ChevronDown className="w-4 h-4 text-gray-500" />
            : <ChevronRight className="w-4 h-4 text-gray-500" />}
          <span className="font-medium text-sm">{category}</span>
          <Badge variant="secondary" className="text-xs">{items.length}</Badge>
          {failureCount > 0 && (
            <Badge variant="destructive" className="text-xs">{failureCount} 失败</Badge>
          )}
          {progressCount > 0 && (
            <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">
              {progressCount} 可续继
            </Badge>
          )}
        </div>
      </div>
      {expanded && (
        <>
          <div className="grid grid-cols-12 gap-2 px-3 py-1.5 bg-gray-50 border-b text-xs text-gray-500 font-medium">
            <div className="col-span-3">数据表</div>
            <div className="col-span-3">增量同步</div>
            <div className="col-span-2">全量同步</div>
            <div className="col-span-2">策略</div>
            <div className="col-span-2 text-right">操作</div>
          </div>
          {items.map(item => (
            <SyncRow
              key={item.table_key}
              item={item}
              onSync={onSync}
              onClearProgress={onClearProgress}
              onEdit={onEdit}
              onTest={onTest}
            />
          ))}
        </>
      )}
    </Card>
  )
}
