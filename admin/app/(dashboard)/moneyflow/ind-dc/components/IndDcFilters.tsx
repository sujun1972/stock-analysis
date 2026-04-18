'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ListFilter } from 'lucide-react'

interface IndDcFiltersProps {
  tradeDate: Date | undefined
  onTradeDateChange: (date: Date | undefined) => void
  contentType: string
  onContentTypeChange: (value: string) => void
  onQuery: () => void
  isLoading: boolean
}

export function IndDcFilters({
  tradeDate,
  onTradeDateChange,
  contentType,
  onContentTypeChange,
  onQuery,
  isLoading,
}: IndDcFiltersProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ListFilter className="h-5 w-5" />
          数据查询
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1 w-full sm:w-auto">
            <label className="text-sm font-medium mb-1 block">交易日期</label>
            <DatePicker date={tradeDate} onDateChange={onTradeDateChange} />
          </div>
          <div className="w-full sm:w-40">
            <label className="text-sm font-medium mb-1 block">板块类型</label>
            <Select value={contentType} onValueChange={onContentTypeChange}>
              <SelectTrigger>
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="行业">行业</SelectItem>
                <SelectItem value="概念">概念</SelectItem>
                <SelectItem value="地域">地域</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <Button onClick={onQuery} disabled={isLoading} className="flex-1 sm:flex-none">
              查询
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
