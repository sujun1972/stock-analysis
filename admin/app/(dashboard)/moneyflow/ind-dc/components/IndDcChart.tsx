'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface ChartItem {
  name: string
  主力净流入: number
  超大单: number
  大单: number
}

interface IndDcChartProps {
  chartData: ChartItem[]
}

export function IndDcChart({ chartData }: IndDcChartProps) {
  if (chartData.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          主力资金流入 TOP 20 板块
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div style={{ minWidth: '600px' }}>
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={0}
                  tick={{ fontSize: 11 }}
                />
                <YAxis tickFormatter={(v) => v.toFixed(1)} />
                <Tooltip formatter={(v) => typeof v === 'number' ? v.toFixed(2) + '亿' : '-'} />
                <Legend />
                <Bar dataKey="主力净流入" fill="#8884d8" />
                <Bar dataKey="超大单" fill="#82ca9d" />
                <Bar dataKey="大单" fill="#ffc658" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
