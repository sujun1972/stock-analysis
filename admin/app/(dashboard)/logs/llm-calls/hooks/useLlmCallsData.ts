/**
 * LLM调用日志数据加载 Hook
 * 管理查询参数、日期选择、详情弹窗状态和数据获取
 */

'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getLLMCallLogs,
  getLLMSummary,
  type LLMCallLog,
  type LLMCallLogQuery,
} from '@/lib/llm-logs-api'
import { format } from 'date-fns'
import { zhCN as dateZhCN } from 'date-fns/locale'

export function useLlmCallsData() {
  // 查询参数
  const [queryParams, setQueryParams] = useState<LLMCallLogQuery>({
    page: 1,
    page_size: 20
  })

  // 日期选择状态
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined)

  // 详情弹窗
  const [detailLog, setDetailLog] = useState<LLMCallLog | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // 获取日志列表
  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['llm-logs', queryParams],
    queryFn: () => getLLMCallLogs(queryParams),
  })

  // 获取概览数据
  const { data: summaryData } = useQuery({
    queryKey: ['llm-summary', 7],
    queryFn: () => getLLMSummary(7),
  })

  const logs = logsData?.data?.logs || []
  const pagination = logsData?.data?.pagination
  const summary = summaryData

  // 查看详情
  const handleViewDetail = (log: LLMCallLog) => {
    setDetailLog(log)
    setDetailOpen(true)
  }

  // 格式化时间
  const formatDateTime = (dateStr: string) => {
    try {
      return format(new Date(dateStr), 'yyyy-MM-dd HH:mm:ss', { locale: dateZhCN })
    } catch {
      return dateStr
    }
  }

  // 格式化耗时
  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  // 格式化成本
  const formatCost = (cost: number | null) => {
    if (!cost) return '-'
    return `$${cost.toFixed(4)}`
  }

  return {
    // 状态
    queryParams,
    setQueryParams,
    selectedDate,
    setSelectedDate,
    detailLog,
    detailOpen,
    setDetailOpen,
    // 数据
    logs,
    pagination,
    summary,
    isLoading,
    refetch,
    // 操作
    handleViewDetail,
    // 工具函数
    formatDateTime,
    formatDuration,
    formatCost,
  }
}
