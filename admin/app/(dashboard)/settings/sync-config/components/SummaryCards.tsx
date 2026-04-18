'use client'

import { Card } from '@/components/ui/card'
import type { SyncOverviewItem } from '@/lib/api/sync-dashboard'

export function SummaryCards({ items }: { items: SyncOverviewItem[] }) {
  const totalTables = items.length
  const failedTables = items.filter(
    i => i.last_incremental?.status === 'failure' || i.last_full_sync?.status === 'failure'
  ).length
  const pendingProgress = items.filter(i => i.redis_progress).length
  const neverSynced = items.filter(i => !i.last_incremental && !i.last_full_sync).length

  const stats = [
    { label: '数据表总数', value: totalTables, color: 'text-blue-600' },
    { label: '从未同步', value: neverSynced, color: 'text-gray-500' },
    { label: '有失败记录', value: failedTables, color: 'text-red-500' },
    { label: '有续继进度', value: pendingProgress, color: 'text-orange-500' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {stats.map(stat => (
        <Card key={stat.label} className="p-3">
          <p className="text-xs text-gray-500">{stat.label}</p>
          <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
        </Card>
      ))}
    </div>
  )
}
