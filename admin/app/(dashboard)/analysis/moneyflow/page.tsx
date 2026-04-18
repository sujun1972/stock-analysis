'use client'

import { useEffect, useState } from 'react'
import { axiosInstance } from '@/lib/api'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Search,
  RefreshCw,
  AlertTriangle,
  ArrowUpCircle,
  ArrowDownCircle
} from 'lucide-react'

interface MoneyflowData {
  ts_code: string
  name: string
  trade_date: string
  net_mf_amount: number
  buy_elg_amount: number
  sell_elg_amount: number
  buy_lg_amount: number
  sell_lg_amount: number
  buy_md_amount: number
  sell_md_amount: number
  buy_sm_amount: number
  sell_sm_amount: number
  trade_count: number
}

interface MoneyflowStats {
  totalInflow: number
  totalOutflow: number
  netFlow: number
  topInflowCount: number
  topOutflowCount: number
}

export default function MoneyflowAnalysisPage() {
  const [moneyflowData, setMoneyflowData] = useState<MoneyflowData[]>([])
  const [stats, setStats] = useState<MoneyflowStats>({
    totalInflow: 0,
    totalOutflow: 0,
    netFlow: 0,
    topInflowCount: 0,
    topOutflowCount: 0
  })
  const [loading, setLoading] = useState(true)
  const [searchCode, setSearchCode] = useState('')
  const [dateFilter, setDateFilter] = useState('today')
  const [sortBy, setSortBy] = useState<'net_inflow' | 'large_inflow' | 'trade_count'>('net_inflow')

  useEffect(() => {
    loadMoneyflowData()
  }, [dateFilter, sortBy])

  const loadMoneyflowData = async () => {
    try {
      setLoading(true)
      // 模拟数据，实际应调用API
      const mockData: MoneyflowData[] = [
        {
          ts_code: '000001.SZ',
          name: '平安银行',
          trade_date: '2024-03-17',
          net_mf_amount: 15234.56,
          buy_elg_amount: 8234.56,
          sell_elg_amount: 3234.12,
          buy_lg_amount: 5234.78,
          sell_lg_amount: 2234.90,
          buy_md_amount: 3456.78,
          sell_md_amount: 2345.67,
          buy_sm_amount: 2345.67,
          sell_sm_amount: 3456.78,
          trade_count: 12345
        },
        {
          ts_code: '000002.SZ',
          name: '万科A',
          trade_date: '2024-03-17',
          net_mf_amount: -8234.56,
          buy_elg_amount: 2234.56,
          sell_elg_amount: 5234.12,
          buy_lg_amount: 1234.78,
          sell_lg_amount: 3234.90,
          buy_md_amount: 2456.78,
          sell_md_amount: 3345.67,
          buy_sm_amount: 3345.67,
          sell_sm_amount: 4456.78,
          trade_count: 8765
        },
        // ... 更多数据
      ]

      setMoneyflowData(mockData)

      // 计算统计数据
      const inflow = mockData.filter(d => d.net_mf_amount > 0)
      const outflow = mockData.filter(d => d.net_mf_amount < 0)

      setStats({
        totalInflow: inflow.reduce((sum, d) => sum + d.net_mf_amount, 0),
        totalOutflow: Math.abs(outflow.reduce((sum, d) => sum + d.net_mf_amount, 0)),
        netFlow: mockData.reduce((sum, d) => sum + d.net_mf_amount, 0),
        topInflowCount: inflow.length,
        topOutflowCount: outflow.length
      })
    } catch (error) {
      console.error('加载资金流向数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    if (searchCode) {
      // 实际应调用API搜索
      console.log('搜索股票:', searchCode)
    }
  }

  const columns: Column<MoneyflowData>[] = [
    {
      key: 'ts_code',
      header: '股票',
      render: (value: string, item: MoneyflowData) => (
        <div>
          <div className="font-medium text-sm">{item.name}</div>
          <div className="text-xs text-gray-500">{value}</div>
        </div>
      ),
      width: 120
    },
    {
      key: 'net_mf_amount',
      header: '净流入(万)',
      render: (value: number) => (
        <div className={`font-medium ${value > 0 ? 'text-red-600' : 'text-green-600'}`}>
          {value > 0 && '+'}
          {value.toFixed(2)}
        </div>
      ),
      sortable: true
    },
    {
      key: 'buy_elg_amount',
      header: '特大单买入',
      render: (value: number, item: MoneyflowData) => (
        <div className="text-xs">
          <div className="text-red-600">+{value.toFixed(2)}</div>
          <div className="text-green-600">-{item.sell_elg_amount.toFixed(2)}</div>
        </div>
      )
    },
    {
      key: 'buy_lg_amount',
      header: '大单买入',
      render: (value: number, item: MoneyflowData) => (
        <div className="text-xs">
          <div className="text-red-600">+{value.toFixed(2)}</div>
          <div className="text-green-600">-{item.sell_lg_amount.toFixed(2)}</div>
        </div>
      )
    },
    {
      key: 'buy_md_amount',
      header: '中单买入',
      render: (value: number, item: MoneyflowData) => (
        <div className="text-xs">
          <div className="text-red-600">+{value.toFixed(2)}</div>
          <div className="text-green-600">-{item.sell_md_amount.toFixed(2)}</div>
        </div>
      )
    },
    {
      key: 'buy_sm_amount',
      header: '小单买入',
      render: (value: number, item: MoneyflowData) => (
        <div className="text-xs">
          <div className="text-red-600">+{value.toFixed(2)}</div>
          <div className="text-green-600">-{item.sell_sm_amount.toFixed(2)}</div>
        </div>
      )
    },
    {
      key: 'trade_count',
      header: '成交笔数',
      render: (value: number) => (
        <span className="text-sm">{value.toLocaleString()}</span>
      )
    }
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="资金流向分析"
        description="追踪主力资金动向，把握市场脉搏"
      />

      {/* 资金流向统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总流入</CardTitle>
            <ArrowUpCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              +{(stats.totalInflow / 10000).toFixed(2)} 亿
            </div>
            <p className="text-xs text-gray-600 mt-1">
              {stats.topInflowCount} 只股票净流入
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总流出</CardTitle>
            <ArrowDownCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              -{(stats.totalOutflow / 10000).toFixed(2)} 亿
            </div>
            <p className="text-xs text-gray-600 mt-1">
              {stats.topOutflowCount} 只股票净流出
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">净流向</CardTitle>
            <DollarSign className="h-4 w-4 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stats.netFlow > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {stats.netFlow > 0 && '+'}
              {(stats.netFlow / 10000).toFixed(2)} 亿
            </div>
            <p className="text-xs text-gray-600 mt-1">
              市场整体{stats.netFlow > 0 ? '流入' : '流出'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 筛选工具栏 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 flex gap-2">
              <Input
                placeholder="输入股票代码或名称"
                value={searchCode}
                onChange={(e) => setSearchCode(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch}>
                <Search className="h-4 w-4" />
              </Button>
            </div>

            <Select value={dateFilter} onValueChange={setDateFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="today">今日</SelectItem>
                <SelectItem value="3days">近3日</SelectItem>
                <SelectItem value="5days">近5日</SelectItem>
                <SelectItem value="10days">近10日</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(v) => setSortBy(v as any)}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="net_inflow">净流入排序</SelectItem>
                <SelectItem value="large_inflow">大单流入排序</SelectItem>
                <SelectItem value="trade_count">成交量排序</SelectItem>
              </SelectContent>
            </Select>

            <Button variant="outline" onClick={loadMoneyflowData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 资金流向数据表 */}
      <Card>
        <CardHeader>
          <CardTitle>主力资金流向TOP100</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={moneyflowData}
          />
        </CardContent>
      </Card>

      {/* 提示信息 */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <p className="font-semibold mb-2">数据说明</p>
          <ul className="text-xs space-y-1 list-disc list-inside">
            <li>特大单：单笔成交金额≥100万元</li>
            <li>大单：50万元≤单笔成交金额&lt;100万元</li>
            <li>中单：10万元≤单笔成交金额&lt;50万元</li>
            <li>小单：单笔成交金额&lt;10万元</li>
            <li>资金流向数据每日17:30更新，积分消耗2000点</li>
          </ul>
        </AlertDescription>
      </Alert>
    </div>
  )
}