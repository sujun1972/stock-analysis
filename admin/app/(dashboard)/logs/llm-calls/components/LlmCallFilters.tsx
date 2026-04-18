/**
 * LLM调用日志筛选面板
 * 支持按业务类型、提供商、状态和日期进行筛选
 */

'use client'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { CalendarIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LLMCallLogQuery } from '@/lib/llm-logs-api'
import { format } from 'date-fns'
import { zhCN } from '@/lib/date-utils'

interface LlmCallFiltersProps {
  queryParams: LLMCallLogQuery
  setQueryParams: (params: LLMCallLogQuery) => void
  selectedDate: Date | undefined
  setSelectedDate: (date: Date | undefined) => void
}

export function LlmCallFilters({
  queryParams,
  setQueryParams,
  selectedDate,
  setSelectedDate,
}: LlmCallFiltersProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base sm:text-lg">筛选条件</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Select
            value={queryParams.business_type || 'all'}
            onValueChange={(value) =>
              setQueryParams({ ...queryParams, business_type: value === 'all' ? undefined : value as any, page: 1 })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="业务类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部业务</SelectItem>
              <SelectItem value="sentiment_analysis">市场情绪分析</SelectItem>
              <SelectItem value="premarket_analysis">盘前碰撞分析</SelectItem>
              <SelectItem value="strategy_generation">策略代码生成</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={queryParams.provider || 'all'}
            onValueChange={(value) =>
              setQueryParams({ ...queryParams, provider: value === 'all' ? undefined : value, page: 1 })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="AI提供商" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部提供商</SelectItem>
              <SelectItem value="deepseek">DeepSeek</SelectItem>
              <SelectItem value="gemini">Gemini</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={queryParams.status || 'all'}
            onValueChange={(value) =>
              setQueryParams({ ...queryParams, status: value === 'all' ? undefined : value as any, page: 1 })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="success">成功</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
              <SelectItem value="timeout">超时</SelectItem>
              <SelectItem value="rate_limited">限流</SelectItem>
            </SelectContent>
          </Select>

          <div className="w-full">
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "w-full justify-start text-left font-normal",
                    !selectedDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4 flex-shrink-0" />
                  {selectedDate ? (
                    <span className="truncate">
                      {format(selectedDate, "yyyy-MM-dd", { locale: zhCN })}
                    </span>
                  ) : (
                    <span className="truncate">选择开始日期</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={(date) => {
                    setSelectedDate(date)
                    setQueryParams({
                      ...queryParams,
                      start_date: date ? format(date, "yyyy-MM-dd") : undefined,
                      page: 1
                    })
                  }}
                  locale={zhCN}
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
