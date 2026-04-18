'use client'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable } from '@/components/common/DataTable'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { useLlmCallsData, useLlmCallTable } from './hooks'
import { LlmCallSummaryCards, LlmCallFilters, LlmCallDetailDialog } from './components'

export default function LLMCallLogsPage() {
  const {
    queryParams,
    setQueryParams,
    selectedDate,
    setSelectedDate,
    detailLog,
    detailOpen,
    setDetailOpen,
    logs,
    pagination,
    summary,
    isLoading,
    refetch,
    handleViewDetail,
    formatDateTime,
    formatDuration,
    formatCost,
  } = useLlmCallsData()

  const { columns, mobileCard, actions } = useLlmCallTable({
    formatDateTime,
    formatDuration,
    formatCost,
    handleViewDetail,
  })

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="LLM调用日志"
        description="查看和管理所有AI模型调用记录"
        actions={
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </Button>
        }
      />

      {/* 概览卡片 */}
      {summary && <LlmCallSummaryCards summary={summary} />}

      {/* 筛选器 */}
      <LlmCallFilters
        queryParams={queryParams}
        setQueryParams={setQueryParams}
        selectedDate={selectedDate}
        setSelectedDate={setSelectedDate}
      />

      {/* 日志列表 - 使用 DataTable 组件 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">调用记录</CardTitle>
          <CardDescription>
            共 {pagination?.total || 0} 条记录
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={logs}
            columns={columns}
            loading={isLoading}
            emptyMessage="暂无数据"
            loadingMessage="加载中..."
            pagination={
              pagination ? {
                page: queryParams.page || 1,
                pageSize: queryParams.page_size || 20,
                total: pagination.total,
                onPageChange: (page) => setQueryParams({ ...queryParams, page }),
              } : undefined
            }
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(log) => log.call_id}
          />
        </CardContent>
      </Card>

      {/* 详情弹窗 */}
      <LlmCallDetailDialog
        log={detailLog}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        formatDuration={formatDuration}
        formatCost={formatCost}
      />
    </div>
  )
}
