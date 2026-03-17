'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, Globe } from 'lucide-react'

interface NorthBoundData {
  code: string
  name: string
  vol: number
  ratio: number
  exchange: string
  change: number
}

export default function NorthBoundPage() {
  const mockData: NorthBoundData[] = [
    { code: '000002', name: '万科A', vol: 123456789, ratio: 2.34, exchange: 'SZ', change: 0.23 },
    { code: '600519', name: '贵州茅台', vol: 98765432, ratio: 1.89, exchange: 'SH', change: -0.12 },
  ]

  const columns: Column<NorthBoundData>[] = [
    {
      key: 'code',
      header: '股票',
      render: (_: string, item: NorthBoundData) => (
        <div>
          <div className="font-medium">{item.name}</div>
          <div className="text-xs text-gray-500">{item.code}</div>
        </div>
      )
    },
    {
      key: 'vol',
      header: '持股数量',
      render: (value: number) => (
        <span>{(value / 100000000).toFixed(2)}亿股</span>
      )
    },
    {
      key: 'ratio',
      header: '持股占比',
      render: (value: number) => (
        <span className="font-medium">{value.toFixed(2)}%</span>
      )
    },
    {
      key: 'change',
      header: '变动',
      render: (value: number) => (
        <span className={value > 0 ? 'text-red-600' : 'text-green-600'}>
          {value > 0 && '+'}{value.toFixed(2)}%
        </span>
      )
    },
    {
      key: 'exchange',
      header: '市场',
      render: (value: string) => (
        <Badge variant="outline">{value === 'SH' ? '沪股通' : '深股通'}</Badge>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="北向资金监控"
        description="追踪沪深港通北向资金流向"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日净流入</CardTitle>
            <Globe className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">+23.45 亿</div>
            <p className="text-xs text-gray-600 mt-1">沪股通 +15.23亿 深股通 +8.22亿</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">本月累计</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+456.78 亿</div>
            <p className="text-xs text-gray-600 mt-1">连续15日净流入</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">持股市值</CardTitle>
            <Globe className="h-4 w-4 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.34 万亿</div>
            <p className="text-xs text-gray-600 mt-1">占A股总市值 3.2%</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>北向资金持股TOP50</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={mockData} pageSize={20} />
        </CardContent>
      </Card>
    </div>
  )
}