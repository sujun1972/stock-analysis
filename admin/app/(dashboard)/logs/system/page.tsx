/**
 * 系统日志页面（新版 - 读取日志文件）
 *
 * 功能：
 * - 查看backend/logs目录下的JSON格式日志文件
 * - 支持按类型、级别、模块、关键词过滤
 * - 实时统计和分析
 *
 * 响应式设计：
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 */
'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  FileText,
  Activity,
  AlertCircle,
  RefreshCw,
  Search,
  Calendar,
  Filter,
  Zap,
  TrendingUp
} from 'lucide-react'
import { DataTable, Column } from '@/components/common/DataTable'

interface SystemLogRecord {
  text: string
  timestamp: string
  level: string
  module?: string
  function?: string
  line?: number
  message: string
  file_path?: string
  extra?: any
}

interface LogStatistics {
  total_logs: number
  by_level: Record<string, number>
  by_module: Record<string, number>
  error_count: number
  warning_count: number
}

type LogType = 'app' | 'errors' | 'performance'
type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'all'

export default function SystemLogsPage() {
  const [logType, setLogType] = useState<LogType>('app')
  const [logs, setLogs] = useState<SystemLogRecord[]>([])
  const [statistics, setStatistics] = useState<LogStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 过滤条件
  const [levelFilter, setLevelFilter] = useState<LogLevel>('all')
  const [moduleFilter, setModuleFilter] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 50

  const loadLogs = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      // 查询日志
      const logsResponse = await apiClient.querySystemLogs({
        log_type: logType,
        level: levelFilter === 'all' ? undefined : levelFilter,
        module: moduleFilter || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize
      }) as any

      if (logsResponse?.code === 200 && logsResponse.data) {
        setLogs(logsResponse.data.logs)
        setTotal(logsResponse.data.total)
      } else {
        setError(logsResponse?.message || '加载日志失败')
      }

      // 获取统计信息
      const statsResponse = await apiClient.getSystemLogStatistics({
        log_type: logType
      }) as any

      if (statsResponse?.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || '加载日志失败')
      console.error('Failed to load system logs:', err)
    } finally {
      setIsLoading(false)
    }
  }, [logType, levelFilter, moduleFilter, searchTerm, page])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  const getLevelBadge = (level: string) => {
    const colors: Record<string, string> = {
      'DEBUG': 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
      'INFO': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'WARNING': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      'ERROR': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'CRITICAL': 'bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100',
    }

    return (
      <Badge className={colors[level] || 'bg-gray-100 text-gray-800'}>
        {level}
      </Badge>
    )
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const handleClearFilters = () => {
    setLevelFilter('all')
    setModuleFilter('')
    setSearchTerm('')
    setPage(1)
  }

  const totalPages = Math.ceil(total / pageSize)

  // 定义表格列配置
  const columns: Column<SystemLogRecord>[] = useMemo(() => [
    {
      key: 'timestamp',
      header: '时间',
      accessor: (item: SystemLogRecord) => (
        <span className="text-sm font-mono">
          {formatTimestamp(item.timestamp)}
        </span>
      ),
      width: 180
    },
    {
      key: 'level',
      header: '级别',
      accessor: (item: SystemLogRecord) => getLevelBadge(item.level),
      width: 80
    },
    {
      key: 'module',
      header: '模块',
      accessor: (item: SystemLogRecord) => (
        <span className="text-sm">{item.module || '-'}</span>
      ),
      width: 120
    },
    {
      key: 'function',
      header: '函数',
      accessor: (item: SystemLogRecord) => (
        <span className="text-sm">
          {item.function && item.line ? `${item.function}:${item.line}` : '-'}
        </span>
      ),
      width: 120
    },
    {
      key: 'message',
      header: '消息',
      cellClassName: 'text-sm'
    }
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((log: SystemLogRecord) => (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-xs text-gray-500 font-mono">
            {formatTimestamp(log.timestamp)}
          </div>
          <div className="text-sm mt-1">
            <span className="text-gray-500">模块: </span>
            {log.module || '-'} / {log.function || '-'}
          </div>
        </div>
        {getLevelBadge(log.level)}
      </div>

      <div className="text-sm text-gray-700 dark:text-gray-300">
        {log.message}
      </div>
    </div>
  ), [])

  // 处理分页变化
  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="系统日志"
        description="查看和分析应用程序运行日志"
        actions={
          <Button onClick={loadLogs} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                总日志数
              </CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_logs.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-2">
                {logType === 'app' ? '应用日志' : logType === 'errors' ? '错误日志' : '性能日志'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                错误数量
              </CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.error_count}</div>
              <p className="text-xs text-muted-foreground mt-2">
                ERROR + CRITICAL 级别
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                警告数量
              </CardTitle>
              <Zap className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{statistics.warning_count}</div>
              <p className="text-xs text-muted-foreground mt-2">
                WARNING 级别
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                当前页
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{page} / {totalPages || 1}</div>
              <p className="text-xs text-muted-foreground mt-2">
                共 {total} 条记录
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 日志类型选择 */}
      <Card>
        <CardContent className="pt-6">
          <Tabs value={logType} onValueChange={(v) => {
            setLogType(v as LogType)
            setPage(1)
          }}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="app">应用日志</TabsTrigger>
              <TabsTrigger value="errors">错误日志</TabsTrigger>
              <TabsTrigger value="performance">性能日志</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {/* 过滤器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">日志级别</label>
              <Select value={levelFilter} onValueChange={(v) => {
                setLevelFilter(v as LogLevel)
                setPage(1)
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="选择级别" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="DEBUG">DEBUG</SelectItem>
                  <SelectItem value="INFO">INFO</SelectItem>
                  <SelectItem value="WARNING">WARNING</SelectItem>
                  <SelectItem value="ERROR">ERROR</SelectItem>
                  <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">模块名称</label>
              <Input
                placeholder="如: api, core, services"
                value={moduleFilter}
                onChange={(e) => {
                  setModuleFilter(e.target.value)
                  setPage(1)
                }}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">搜索关键词</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="搜索日志消息..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setPage(1)
                  }}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={handleClearFilters}
                className="w-full"
              >
                <Filter className="h-4 w-4 mr-2" />
                清除过滤
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 日志表格 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            日志记录
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8 text-red-600">{error}</div>
          ) : (
            <DataTable
              data={logs}
              columns={columns}
              loading={isLoading}
              mobileCard={mobileCard}
              pagination={{
                page,
                pageSize,
                total,
                onPageChange: handlePageChange
              }}
              emptyMessage="暂无日志记录"
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}