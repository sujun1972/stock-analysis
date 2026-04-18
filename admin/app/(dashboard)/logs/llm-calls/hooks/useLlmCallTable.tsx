'use client'

import { useMemo, useCallback } from 'react'
import { type Column } from '@/components/common/DataTable'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Eye } from 'lucide-react'
import {
  type LLMCallLog,
  businessTypeMap,
  statusMap,
  providerMap,
} from '@/lib/llm-logs-api'

interface UseLlmCallTableOptions {
  formatDateTime: (dateStr: string) => string
  formatDuration: (ms: number | null) => string
  formatCost: (cost: number | null) => string
  handleViewDetail: (log: LLMCallLog) => void
}

export function useLlmCallTable({
  formatDateTime,
  formatDuration,
  formatCost,
  handleViewDetail,
}: UseLlmCallTableOptions) {
  const columns: Column<LLMCallLog>[] = useMemo(() => [
    {
      key: 'created_at',
      header: '调用时间',
      accessor: (log) => (
        <span className="text-sm">{formatDateTime(log.created_at)}</span>
      ),
    },
    {
      key: 'business_type',
      header: '业务类型',
      accessor: (log) => (
        <span className="text-sm">
          {businessTypeMap[log.business_type] || log.business_type}
        </span>
      ),
      hideOnMobile: true,
    },
    {
      key: 'provider',
      header: '提供商',
      accessor: (log) => (
        <Badge variant="outline">
          {providerMap[log.provider] || log.provider}
        </Badge>
      ),
    },
    {
      key: 'model_name',
      header: '模型',
      cellClassName: 'text-sm font-mono',
      hideOnMobile: true,
    },
    {
      key: 'status',
      header: '状态',
      accessor: (log) => (
        <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
          {statusMap[log.status]?.text || log.status}
        </Badge>
      ),
    },
    {
      key: 'tokens_total',
      header: 'Tokens',
      accessor: (log) => (
        <span className="text-sm">{log.tokens_total?.toLocaleString() || '-'}</span>
      ),
      align: 'right',
      hideOnMobile: true,
    },
    {
      key: 'cost_estimate',
      header: '成本',
      accessor: (log) => (
        <span className="text-sm">{formatCost(log.cost_estimate)}</span>
      ),
      align: 'right',
    },
    {
      key: 'duration_ms',
      header: '耗时',
      accessor: (log) => (
        <span className="text-sm">{formatDuration(log.duration_ms)}</span>
      ),
      align: 'right',
      hideOnMobile: true,
    },
  ], [formatDateTime, formatDuration, formatCost])

  const mobileCard = useCallback((log: LLMCallLog) => (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="text-sm text-gray-600">{formatDateTime(log.created_at)}</div>
          <div className="font-medium mt-1">
            {businessTypeMap[log.business_type] || log.business_type}
          </div>
        </div>
        <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
          {statusMap[log.status]?.text || log.status}
        </Badge>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="outline">
          {providerMap[log.provider] || log.provider}
        </Badge>
        <span className="text-sm font-mono text-gray-600">{log.model_name}</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div>
          <div className="text-gray-500">Tokens</div>
          <div className="font-medium">{log.tokens_total?.toLocaleString() || '-'}</div>
        </div>
        <div>
          <div className="text-gray-500">成本</div>
          <div className="font-medium">{formatCost(log.cost_estimate)}</div>
        </div>
        <div>
          <div className="text-gray-500">耗时</div>
          <div className="font-medium">{formatDuration(log.duration_ms)}</div>
        </div>
      </div>

      <div className="pt-2 border-t">
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleViewDetail(log)}
          className="w-full"
        >
          <Eye className="w-4 h-4 mr-2" />
          查看详情
        </Button>
      </div>
    </div>
  ), [formatDateTime, formatDuration, formatCost, handleViewDetail])

  const actions = useCallback((log: LLMCallLog) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleViewDetail(log)}
    >
      <Eye className="w-4 h-4" />
    </Button>
  ), [handleViewDetail])

  return { columns, mobileCard, actions }
}
