'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { stockAnnsApi, type StockAnnsItem, type AnnoTypeStat } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import {
  ListFilter, RefreshCw, ExternalLink, FileText, Calendar,
} from 'lucide-react'

export default function StockAnnsPage() {
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [annoType, setAnnoType] = useState<string>('ALL')
  const [keyword, setKeyword] = useState('')
  const [annoTypes, setAnnoTypes] = useState<AnnoTypeStat[]>([])
  const { config } = useSystemConfig()

  const openStockAnalysis = (code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  const dp = useDataPage<StockAnnsItem>({
    apiCall: (params) => stockAnnsApi.getData(params),
    syncFn: () => stockAnnsApi.syncAsync(),
    taskName: 'tasks.sync_stock_anns',
    bulkOps: {
      tableKey: 'stock_anns',
      syncFn: (p) => stockAnnsApi.syncFullHistory(p),
      taskName: 'tasks.sync_stock_anns_full_history',
    },
    paginationMode: 'page',
    pageSize: 50,
    buildParams: () => {
      const p: Record<string, unknown> = {}
      if (tsCode.trim()) p.ts_code = tsCode.trim()
      if (startDate) p.start_date = toDateStr(startDate)
      if (endDate) p.end_date = toDateStr(endDate)
      if (annoType !== 'ALL') p.anno_type = annoType
      if (keyword.trim()) p.keyword = keyword.trim()
      return p
    },
    syncSuccessMessage: '公司公告增量同步完成',
  })

  // 首次加载公告类型下拉项
  useEffect(() => {
    stockAnnsApi.getAnnoTypes(90, 200)
      .then((res: any) => {
        const items = res?.data?.items || []
        setAnnoTypes(items)
      })
      .catch(() => setAnnoTypes([]))
  }, [])

  const columns: Column<StockAnnsItem>[] = [
    {
      key: 'ann_date',
      header: '日期',
      accessor: (row) => row.ann_date,
      width: 110,
      cellClassName: 'whitespace-nowrap text-center',
    },
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline whitespace-nowrap"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.stock_name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'anno_type',
      header: '类型',
      accessor: (row) => row.anno_type || '—',
      width: 140,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'title',
      header: '公告标题',
      accessor: (row) => (
        <div className="flex items-center gap-2">
          <span className="truncate" title={row.title}>{row.title}</span>
          {row.has_content && (
            <span title="已抓取正文" className="inline-flex">
              <FileText className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
            </span>
          )}
        </div>
      ),
      cellClassName: 'max-w-0',
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

  const mobileCard = (item: StockAnnsItem) => (
    <div className="space-y-2">
      <div className="flex justify-between items-start pb-2 border-b gap-2">
        <div className="flex-1 min-w-0">
          <span
            className="font-medium cursor-pointer hover:underline"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.stock_name || '-'}
          </span>
          <span className="text-xs text-gray-500 ml-2">{formatStockCode(item.ts_code)}</span>
        </div>
        <span className="text-xs text-gray-500 whitespace-nowrap">{item.ann_date}</span>
      </div>
      <div className="text-sm">
        <div className="text-gray-500 text-xs mb-1">{item.anno_type || '—'}</div>
        <div className="break-words">{item.title}</div>
      </div>
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

  const topAnnoTypes = useMemo(
    () => (annoTypes || []).slice(0, 30),
    [annoTypes]
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="公司公告"
        description="A股公司公告元数据（标题 / 类型 / 日期 / URL），来源：AkShare 东方财富聚合（免费）"
        details={
          <>
            <div>数据源：AkShare ak.stock_notice_report（全市场）+ ak.stock_individual_notice_report（单只）</div>
            <div className="text-xs text-gray-500 mt-1">
              正文按需抓取：
              <Link href="/settings/sync-config" className="text-blue-600 hover:underline ml-1">
                → 同步配置页
              </Link>
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
              tableName="公司公告"
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
              <label className="text-sm font-medium mb-1 block">公告类型</label>
              <Select value={annoType} onValueChange={setAnnoType}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  {topAnnoTypes.map((t) => (
                    <SelectItem key={t.anno_type} value={t.anno_type}>
                      {t.anno_type}（{t.count}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">标题关键字</label>
              <Input
                placeholder="标题模糊匹配"
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
