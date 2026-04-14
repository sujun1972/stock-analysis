'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { stockAiAnalysisApi } from '@/lib/api'
import type { StockAiAnalysisData } from '@/lib/api'
import { toast } from 'sonner'
import { Brain, ListFilter, RefreshCw, FileText, Eye } from 'lucide-react'

const PAGE_SIZE = 20

/** 分析类型中文映射 */
const ANALYSIS_TYPE_LABELS: Record<string, string> = {
  hot_money_view: '游资观点',
  stock_data_collection: '数据采集',
  midline_industry_expert: '中线专家',
  longterm_value_watcher: '长线价值',
  cio_directive: 'CIO指令',
}

/** 分析类型 Badge 颜色 */
const ANALYSIS_TYPE_VARIANTS: Record<string, string> = {
  hot_money_view: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  stock_data_collection: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  midline_industry_expert: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  longterm_value_watcher: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cio_directive: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return dateStr
  }
}

function truncateText(text: string | null | undefined, maxLen: number = 80): string {
  if (!text) return '-'
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

/** JSON 文本尝试格式化，非 JSON 原样返回 */
function formatAnalysisText(text: string | null | undefined): string {
  if (!text) return ''
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

export default function StockAiAnalysisPage() {
  const [data, setData] = useState<StockAiAnalysisData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [tsCode, setTsCode] = useState('')
  const [analysisType, setAnalysisType] = useState('')
  const [aiProvider, setAiProvider] = useState('')
  const [tradeDate, setTradeDate] = useState('')

  // Detail dialog
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailItem, setDetailItem] = useState<StockAiAnalysisData | null>(null)

  const loadData = useCallback(async (targetPage: number = 1) => {
    setIsLoading(true)
    try {
      const params: Record<string, any> = {
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE,
      }
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (analysisType && analysisType !== '__all__') params.analysis_type = analysisType
      if (aiProvider.trim()) params.ai_provider = aiProvider.trim()
      if (tradeDate.trim()) params.trade_date = tradeDate.trim()

      const response = await stockAiAnalysisApi.getList(params)
      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
        setPage(targetPage)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message })
    } finally {
      setIsLoading(false)
    }
  }, [tsCode, analysisType, aiProvider, tradeDate])

  useEffect(() => {
    loadData(1)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleQuery = () => {
    loadData(1)
  }

  const handleViewDetail = (item: StockAiAnalysisData) => {
    setDetailItem(item)
    setDetailOpen(true)
  }

  const columns: Column<StockAiAnalysisData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      width: 110,
      cellClassName: 'whitespace-nowrap font-medium',
      accessor: (row) => row.ts_code,
    },
    {
      key: 'analysis_type',
      header: '分析类型',
      width: 120,
      cellClassName: 'whitespace-nowrap',
      accessor: (row) => {
        const label = ANALYSIS_TYPE_LABELS[row.analysis_type] || row.analysis_type
        const variant = ANALYSIS_TYPE_VARIANTS[row.analysis_type] || 'bg-gray-100 text-gray-700'
        return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${variant}`}>{label}</span>
      },
    },
    {
      key: 'score',
      header: '评分',
      width: 70,
      cellClassName: 'text-center whitespace-nowrap',
      accessor: (row) => {
        if (row.score === null || row.score === undefined) return <span className="text-gray-400">-</span>
        const color = row.score >= 7 ? 'text-red-600 font-semibold' : row.score >= 4 ? 'text-amber-600' : 'text-green-600'
        return <span className={color}>{row.score.toFixed(1)}</span>
      },
    },
    {
      key: 'trade_date',
      header: '交易日',
      width: 100,
      cellClassName: 'whitespace-nowrap text-sm',
      accessor: (row) => {
        if (!row.trade_date) return <span className="text-gray-400">-</span>
        const d = row.trade_date
        return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`
      },
    },
    {
      key: 'analysis_text',
      header: '分析内容',
      cellClassName: 'text-sm text-gray-600 dark:text-gray-400',
      accessor: (row) => (
        <span className="cursor-pointer hover:text-blue-600" onClick={() => handleViewDetail(row)}>
          {truncateText(row.analysis_text, 60)}
        </span>
      ),
    },
    {
      key: 'ai_provider',
      header: 'AI提供商',
      width: 100,
      cellClassName: 'whitespace-nowrap',
      accessor: (row) => row.ai_provider || '-',
    },
    {
      key: 'ai_model',
      header: '模型',
      width: 130,
      cellClassName: 'whitespace-nowrap text-sm',
      accessor: (row) => row.ai_model || '-',
    },
    {
      key: 'version',
      header: '版本',
      width: 60,
      cellClassName: 'text-center whitespace-nowrap',
      accessor: (row) => <span className="text-gray-500">v{row.version}</span>,
    },
    {
      key: 'created_at',
      header: '创建时间',
      width: 150,
      cellClassName: 'whitespace-nowrap text-sm',
      accessor: (row) => formatDate(row.created_at),
    },
    {
      key: 'actions',
      header: '操作',
      width: 60,
      cellClassName: 'text-center',
      accessor: (row) => (
        <Button variant="ghost" size="sm" onClick={() => handleViewDetail(row)}>
          <Eye className="h-4 w-4" />
        </Button>
      ),
    },
  ], []) // eslint-disable-line react-hooks/exhaustive-deps

  const mobileCard = (item: StockAiAnalysisData) => {
    const typeLabel = ANALYSIS_TYPE_LABELS[item.analysis_type] || item.analysis_type
    const typeVariant = ANALYSIS_TYPE_VARIANTS[item.analysis_type] || 'bg-gray-100 text-gray-700'
    return (
      <div className="p-4 hover:bg-blue-50 dark:hover:bg-gray-800" onClick={() => handleViewDetail(item)}>
        <div className="flex justify-between items-start mb-2">
          <div>
            <div className="font-semibold text-base">{item.ts_code}</div>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mt-1 ${typeVariant}`}>{typeLabel}</span>
          </div>
          <div className="text-right">
            {item.score !== null && item.score !== undefined && (
              <div className="text-lg font-bold text-red-600">{item.score.toFixed(1)}</div>
            )}
            <div className="text-xs text-gray-500">v{item.version}</div>
          </div>
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
          {truncateText(item.analysis_text, 100)}
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span>{item.trade_date ? `${item.trade_date.slice(0, 4)}-${item.trade_date.slice(4, 6)}-${item.trade_date.slice(6, 8)}` : ''} | {item.ai_provider}</span>
          <span>{formatDate(item.created_at)}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票AI分析记录"
        description="查看AI助手生成的股票分析结果，包括游资观点、数据采集、中线专家、长线价值和CIO指令等"
        actions={
          <Button variant="outline" onClick={() => loadData(page)} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        }
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">总记录数</p>
                <p className="text-xl sm:text-2xl font-bold">{total}</p>
              </div>
              <FileText className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">当前页记录</p>
                <p className="text-xl sm:text-2xl font-bold">{data.length}</p>
              </div>
              <Brain className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 查询筛选 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="space-y-1 w-full sm:w-48">
              <Label>股票代码</Label>
              <Input
                placeholder="000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
              />
            </div>
            <div className="space-y-1 w-full sm:w-48">
              <Label>分析类型</Label>
              <Select value={analysisType} onValueChange={setAnalysisType}>
                <SelectTrigger>
                  <SelectValue placeholder="全部类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">全部类型</SelectItem>
                  {Object.entries(ANALYSIS_TYPE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1 w-full sm:w-36">
              <Label>交易日</Label>
              <Input
                placeholder="20260414"
                value={tradeDate}
                onChange={(e) => setTradeDate(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
              />
            </div>
            <div className="space-y-1 w-full sm:w-36">
              <Label>AI提供商</Label>
              <Input
                placeholder="如 deepseek"
                value={aiProvider}
                onChange={(e) => setAiProvider(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
              />
            </div>
            <Button onClick={handleQuery} disabled={isLoading}>查询</Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage="暂无AI分析记录"
            mobileCard={mobileCard}
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0"
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (newPage) => loadData(newPage),
            }}
          />
        </CardContent>
      </Card>

      {/* 分析详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              分析详情 - {detailItem?.ts_code}
              {detailItem && (
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${ANALYSIS_TYPE_VARIANTS[detailItem.analysis_type] || ''}`}>
                  {ANALYSIS_TYPE_LABELS[detailItem.analysis_type] || detailItem.analysis_type}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          {detailItem && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">交易日</span>
                  <p className="font-semibold">{detailItem.trade_date ? `${detailItem.trade_date.slice(0, 4)}-${detailItem.trade_date.slice(4, 6)}-${detailItem.trade_date.slice(6, 8)}` : '-'}</p>
                </div>
                <div>
                  <span className="text-gray-500">评分</span>
                  <p className="font-semibold">{detailItem.score !== null ? detailItem.score.toFixed(1) : '-'}</p>
                </div>
                <div>
                  <span className="text-gray-500">版本</span>
                  <p className="font-semibold">v{detailItem.version}</p>
                </div>
                <div>
                  <span className="text-gray-500">AI提供商</span>
                  <p className="font-semibold">{detailItem.ai_provider || '-'}</p>
                </div>
                <div>
                  <span className="text-gray-500">模型</span>
                  <p className="font-semibold">{detailItem.ai_model || '-'}</p>
                </div>
              </div>
              <div>
                <span className="text-sm text-gray-500">创建时间: {formatDate(detailItem.created_at)}</span>
              </div>
              <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900">
                <pre className="whitespace-pre-wrap text-sm font-mono break-words">
                  {formatAnalysisText(detailItem.analysis_text)}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
