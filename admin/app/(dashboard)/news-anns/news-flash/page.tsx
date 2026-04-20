'use client'

import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { newsFlashApi, type NewsFlashItem, type NewsFlashSourceStat } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import {
  ListFilter, RefreshCw, ExternalLink, Calendar,
} from 'lucide-react'

export default function NewsFlashPage() {
  const [source, setSource] = useState<string>('ALL')
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [keyword, setKeyword] = useState('')
  const [sources, setSources] = useState<NewsFlashSourceStat[]>([])
  const { config } = useSystemConfig()

  useEffect(() => {
    newsFlashApi.getData({ page: 1, page_size: 1 })
      .then((res: any) => {
        const s = res?.data?.sources || []
        setSources(s)
      })
      .catch(() => setSources([]))
  }, [])

  const openStockAnalysis = (code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  const dp = useDataPage<NewsFlashItem>({
    apiCall: (params) => newsFlashApi.getData(params),
    syncFn: () => newsFlashApi.syncAsync(),
    taskName: 'tasks.sync_news_flash',
    bulkOps: {
      tableKey: 'news_flash',
      syncFn: (p) => newsFlashApi.syncFullHistory(p),
      taskName: 'tasks.sync_news_flash_full_history',
    },
    paginationMode: 'page',
    pageSize: 50,
    buildParams: () => {
      const p: Record<string, unknown> = {}
      if (source !== 'ALL') p.source = source
      if (tsCode.trim()) p.ts_code = tsCode.trim()
      if (startDate) p.start_time = toDateStr(startDate)
      if (endDate) p.end_time = toDateStr(endDate)
      if (keyword.trim()) p.keyword = keyword.trim()
      return p
    },
    syncSuccessMessage: '财经快讯增量同步完成',
  })

  const columns: Column<NewsFlashItem>[] = [
    {
      key: 'publish_time',
      header: '时间',
      accessor: (row) => (row.publish_time || '').replace('T', ' ').slice(0, 16),
      width: 140,
      cellClassName: 'whitespace-nowrap text-center text-xs',
    },
    {
      key: 'source',
      header: '来源',
      accessor: (row) => row.source,
      width: 90,
      cellClassName: 'whitespace-nowrap text-center',
    },
    {
      key: 'title',
      header: '标题',
      accessor: (row) => (
        <span className="block truncate" title={row.title}>{row.title}</span>
      ),
      cellClassName: 'max-w-0',
    },
    {
      key: 'summary',
      header: '摘要',
      accessor: (row) => (
        <span className="block truncate text-xs text-gray-600" title={row.summary || ''}>
          {row.summary || '—'}
        </span>
      ),
      cellClassName: 'max-w-0',
    },
    {
      key: 'related_ts_codes',
      header: '关联股',
      accessor: (row) => {
        if (!row.related_ts_codes?.length) return <span className="text-gray-400">—</span>
        return (
          <div className="flex flex-wrap gap-1">
            {row.related_ts_codes.slice(0, 3).map((tc) => (
              <span
                key={tc}
                className="text-xs text-blue-600 hover:underline cursor-pointer"
                onClick={() => openStockAnalysis(tc)}
              >
                {formatStockCode(tc)}
              </span>
            ))}
            {row.related_ts_codes.length > 3 && (
              <span className="text-xs text-gray-500">+{row.related_ts_codes.length - 3}</span>
            )}
          </div>
        )
      },
      width: 140,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'url',
      header: '链接',
      accessor: (row) =>
        row.url ? (
          <a
            href={row.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-blue-600 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        ) : '-',
      width: 60,
      cellClassName: 'text-center',
    },
  ]

  const mobileCard = (item: NewsFlashItem) => (
    <div className="space-y-2">
      <div className="flex justify-between items-start pb-2 border-b gap-2">
        <span className="text-xs font-medium">{item.source}</span>
        <span className="text-xs text-gray-500 whitespace-nowrap">
          {(item.publish_time || '').replace('T', ' ').slice(0, 16)}
        </span>
      </div>
      <div className="text-sm font-medium break-words">{item.title}</div>
      {item.summary && (
        <div className="text-xs text-gray-600 break-words line-clamp-3">{item.summary}</div>
      )}
      {item.related_ts_codes?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {item.related_ts_codes.map((tc) => (
            <span
              key={tc}
              className="text-xs text-blue-600 hover:underline cursor-pointer"
              onClick={() => openStockAnalysis(tc)}
            >
              {formatStockCode(tc)}
            </span>
          ))}
        </div>
      )}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          <ExternalLink className="h-3 w-3" /> 查看原文
        </a>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="财经快讯"
        description="财新要闻 + 东财个股新闻（免费替代 Tushare news / major_news）"
        details={
          <>
            <div>数据源：AkShare stock_news_main_cx（宏观/产业快讯）+ stock_news_em（个股新闻）</div>
            <div className="text-xs text-gray-500 mt-1">
              接口无历史参数，靠日常增量积累；建议每 30 分钟增量一次。
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
              tableName="财经快讯"
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 items-end">
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
              <label className="text-sm font-medium mb-1 block">来源</label>
              <Select value={source} onValueChange={setSource}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  {sources.map((s) => (
                    <SelectItem key={s.source} value={s.source}>
                      {s.source}（{s.count}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">关联股票</label>
              <Input
                placeholder="如 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">关键字</label>
              <Input
                placeholder="标题/摘要模糊匹配"
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
