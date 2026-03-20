'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { CreditCard, TrendingUp, TrendingDown } from 'lucide-react'

interface MarginData {
  ts_code: string
  name: string
  rzye: number  // 融资余额
  rqye: number  // 融券余额
  rzrqye: number  // 两融余额
  rzmre: number  // 融资买入额
  rzche: number  // 融资偿还额
}

export default function MarginPage() {
  const mockData: MarginData[] = [
    {
      ts_code: '000001.SZ',
      name: '平安银行',
      rzye: 234567.89,
      rqye: 12345.67,
      rzrqye: 246913.56,
      rzmre: 34567.89,
      rzche: 23456.78
    },
    {
      ts_code: '000002.SZ',
      name: '万科A',
      rzye: 345678.90,
      rqye: 23456.78,
      rzrqye: 369135.68,
      rzmre: 45678.90,
      rzche: 34567.89
    }
  ]

  const columns: Column<MarginData>[] = [
    {
      key: 'ts_code',
      header: '股票',
      render: (_: string, item: MarginData) => (
        <div>
          <div className="font-medium">{item.name}</div>
          <div className="text-xs text-gray-500">{item.ts_code}</div>
        </div>
      )
    },
    {
      key: 'rzye',
      header: '融资余额(万)',
      render: (value: number) => (
        <span className="font-medium">{value.toFixed(2)}</span>
      )
    },
    {
      key: 'rqye',
      header: '融券余额(万)',
      render: (value: number) => (
        <span className="font-medium">{value.toFixed(2)}</span>
      )
    },
    {
      key: 'rzrqye',
      header: '两融余额(万)',
      render: (value: number) => (
        <span className="font-bold text-blue-600">{value.toFixed(2)}</span>
      )
    },
    {
      key: 'rzmre',
      header: '融资买入(万)',
      render: (value: number) => (
        <span className="text-red-600">+{value.toFixed(2)}</span>
      )
    },
    {
      key: 'rzche',
      header: '融资偿还(万)',
      render: (value: number) => (
        <span className="text-green-600">-{value.toFixed(2)}</span>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券分析"
        description="监控两融余额变化，把握市场杠杆水平"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">两融余额</CardTitle>
            <CreditCard className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.68 万亿</div>
            <p className="text-xs text-gray-600 mt-1">较昨日 +123.45亿</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">融资余额</CardTitle>
            <TrendingUp className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.65 万亿</div>
            <p className="text-xs text-gray-600 mt-1">占两融余额 98.2%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">融券余额</CardTitle>
            <TrendingDown className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">300.12 亿</div>
            <p className="text-xs text-gray-600 mt-1">占两融余额 1.8%</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>两融余额TOP100</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={mockData} />
        </CardContent>
      </Card>
    </div>
  )
}