'use client'

import { useMemo, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { type MoneyflowIndDcData, toYi, pctColor } from '../types'

interface IndDcTableProps {
  data: MoneyflowIndDcData[]
  isLoading: boolean
  sortKey: string | null
  sortDirection: 'asc' | 'desc' | null
  onSort: (key: string, direction: 'asc' | 'desc' | null) => void
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export function IndDcTable({
  data,
  isLoading,
  sortKey,
  sortDirection,
  onSort,
  page,
  pageSize,
  total,
  onPageChange,
}: IndDcTableProps) {
  // 表格列定义
  const columns: Column<MoneyflowIndDcData>[] = useMemo(() => [
    {
      key: 'name',
      header: '板块',
      accessor: (row) => row.name ? `${row.name}[${row.ts_code}]` : row.ts_code,
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'content_type',
      header: '类型',
      accessor: (row) => row.content_type,
      width: 70,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null || row.pct_change === undefined) return '-'
        const v = row.pct_change
        return <span className={pctColor(v)}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount',
      header: '主力净流入',
      accessor: (row) => {
        if (row.net_amount === null || row.net_amount === undefined) return '-'
        return <span className={row.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>{toYi(row.net_amount)}</span>
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount_rate',
      header: '主力净占比%',
      accessor: (row) => {
        if (row.net_amount_rate === null || row.net_amount_rate === undefined) return '-'
        const v = row.net_amount_rate
        return <span className={pctColor(v)}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      },
      width: 115,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_elg_amount',
      header: '超大单净流入',
      accessor: (row) => {
        if (row.buy_elg_amount === null || row.buy_elg_amount === undefined) return '-'
        return <span className={row.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_elg_amount)}</span>
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_lg_amount',
      header: '大单净流入',
      accessor: (row) => {
        if (row.buy_lg_amount === null || row.buy_lg_amount === undefined) return '-'
        return <span className={row.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_lg_amount)}</span>
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_md_amount',
      header: '中单净流入',
      accessor: (row) => {
        if (row.buy_md_amount === null || row.buy_md_amount === undefined) return '-'
        return <span className={row.buy_md_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_md_amount)}</span>
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_sm_amount',
      header: '小单净流入',
      accessor: (row) => {
        if (row.buy_sm_amount === null || row.buy_sm_amount === undefined) return '-'
        return <span className={row.buy_sm_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_sm_amount)}</span>
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => row.rank !== null && row.rank !== undefined ? `#${row.rank}` : '-',
      width: 70,
      cellClassName: 'text-center whitespace-nowrap'
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowIndDcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name || item.ts_code}</div>
          <div className="text-sm text-gray-500">{item.ts_code} · {item.content_type}</div>
        </div>
        <div className="text-right">
          {item.pct_change !== null && (
            <div className={pctColor(item.pct_change)}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
          {item.rank !== null && <div className="text-xs text-gray-500">#{item.rank}</div>}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">主力净流入:</span>
          {item.net_amount !== null && (
            <span className={item.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
              {toYi(item.net_amount)}
            </span>
          )}
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">超大单净流入:</span>
          <span className={pctColor(item.buy_elg_amount)}>{toYi(item.buy_elg_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单净流入:</span>
          <span className={pctColor(item.buy_lg_amount)}>{toYi(item.buy_lg_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">主力净占比:</span>
          <span>{item.net_amount_rate !== null ? `${item.net_amount_rate.toFixed(2)}%` : '-'}</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <Card>
      <CardContent className="p-0 sm:p-6">
        <DataTable
          columns={columns}
          data={data}
          loading={isLoading}
          mobileCard={mobileCard}
          emptyMessage="暂无板块资金流向数据"
          tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
          sort={{
            key: sortKey,
            direction: sortDirection,
            onSort,
          }}
          pagination={{
            page,
            pageSize,
            total,
            onPageChange,
          }}
        />
      </CardContent>
    </Card>
  )
}
