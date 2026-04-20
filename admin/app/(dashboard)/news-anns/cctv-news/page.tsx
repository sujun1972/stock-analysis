'use client'

import { useState } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { cctvNewsApi, type CctvNewsItem } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import {
  ListFilter, RefreshCw, Calendar,
} from 'lucide-react'

export default function CctvNewsPage() {
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [keyword, setKeyword] = useState('')

  const dp = useDataPage<CctvNewsItem>({
    apiCall: (params) => cctvNewsApi.getData(params),
    syncFn: () => cctvNewsApi.syncAsync(),
    taskName: 'tasks.sync_cctv_news',
    bulkOps: {
      tableKey: 'cctv_news',
      syncFn: (p) => cctvNewsApi.syncFullHistory(p),
      taskName: 'tasks.sync_cctv_news_full_history',
    },
    paginationMode: 'page',
    pageSize: 50,
    buildParams: () => {
      const p: Record<string, unknown> = {}
      if (startDate) p.start_date = toDateStr(startDate)
      if (endDate) p.end_date = toDateStr(endDate)
      if (keyword.trim()) p.keyword = keyword.trim()
      return p
    },
    syncSuccessMessage: '新闻联播增量同步完成',
  })

  const columns: Column<CctvNewsItem>[] = [
    {
      key: 'news_date',
      header: '日期',
      accessor: (row) => row.news_date,
      width: 110,
      cellClassName: 'whitespace-nowrap text-center',
    },
    {
      key: 'seq_no',
      header: '序号',
      accessor: (row) => row.seq_no,
      width: 70,
      cellClassName: 'text-center text-gray-600',
    },
    {
      key: 'title',
      header: '标题',
      accessor: (row) => (
        <span className="block font-medium truncate" title={row.title}>{row.title}</span>
      ),
      width: 260,
      cellClassName: 'max-w-0',
    },
    {
      key: 'content',
      header: '全文',
      accessor: (row) => (
        <span className="block text-xs text-gray-600 line-clamp-2" title={row.content || ''}>
          {row.content || '—'}
        </span>
      ),
      cellClassName: 'max-w-0',
    },
  ]

  const mobileCard = (item: CctvNewsItem) => (
    <div className="space-y-2">
      <div className="flex justify-between items-start pb-2 border-b gap-2">
        <span className="text-xs text-gray-500 whitespace-nowrap">{item.news_date} · #{item.seq_no}</span>
      </div>
      <div className="text-sm font-medium break-words">{item.title}</div>
      {item.content && (
        <div className="text-xs text-gray-600 break-words line-clamp-4">{item.content}</div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="新闻联播"
        description="CCTV 新闻联播文字稿（免费替代 Tushare cctv_news）"
        details={
          <>
            <div>数据源：AkShare news_cctv（按自然日，覆盖 2016-02 起）</div>
            <div className="text-xs text-gray-500 mt-1">
              单日接口 3-8s；全量覆盖近 5 年约 1500 日、3-4 小时。
            </div>
          </>
        }
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.handleSyncDirect({})} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />增量同步</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="新闻联播"
            />
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" /> 数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
            <div>
              <label className="text-sm font-medium mb-1 flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" /> 起始日期
              </label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">关键字</label>
              <Input
                placeholder="标题/全文模糊匹配"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <div>
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full">
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            mobileCard={mobileCard}
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: dp.sortKey,
              direction: dp.sortDirection,
              onSort: dp.handleSort,
            }}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
