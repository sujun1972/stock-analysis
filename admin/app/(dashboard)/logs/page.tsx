'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  FileText,
  Activity,
  Users,
  RefreshCw,
  Search,
  Calendar,
  Filter
} from 'lucide-react'

interface ActivityLog {
  id: number
  user_id: number | null
  username?: string
  action_type: string
  resource_type: string | null
  resource_id: number | null
  details: any
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

interface LoginHistory {
  id: number
  user_id: number
  username?: string
  ip_address: string | null
  user_agent: string | null
  login_at: string
  status: string
}

export default function LogsPage() {
  const [activeTab, setActiveTab] = useState<'activity' | 'login'>('activity')
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([])
  const [loginHistory, setLoginHistory] = useState<LoginHistory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 过滤条件
  const [actionTypeFilter, setActionTypeFilter] = useState<string>('all')
  const [userIdFilter, setUserIdFilter] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')

  useEffect(() => {
    loadLogs()
  }, [activeTab, actionTypeFilter, userIdFilter])

  const loadLogs = async () => {
    try {
      setIsLoading(true)
      setError(null)

      if (activeTab === 'activity') {
        // 如果后端还没有全局日志API，我们先获取所有用户然后合并日志
        // 这是临时方案，建议后端添加全局日志API
        const usersResponse = await apiClient.getUsers({ page_size: 100 })
        const allLogs: ActivityLog[] = []

        if (usersResponse.data?.items) {
          // 获取每个用户的活动日志
          for (const user of usersResponse.data.items) {
            try {
              const logsResponse = await apiClient.getUserActivityLogs(
                user.id,
                20,
                actionTypeFilter === 'all' ? undefined : actionTypeFilter
              )

              if (logsResponse.data) {
                const logsWithUsername = logsResponse.data.map(log => ({
                  ...log,
                  username: user.username
                }))
                allLogs.push(...logsWithUsername)
              }
            } catch (err) {
              console.error(`Failed to load logs for user ${user.id}:`, err)
            }
          }
        }

        // 按时间排序
        allLogs.sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )

        setActivityLogs(allLogs)
      } else {
        // 获取登录历史
        const usersResponse = await apiClient.getUsers({ page_size: 100 })
        const allHistory: LoginHistory[] = []

        if (usersResponse.data?.items) {
          for (const user of usersResponse.data.items) {
            try {
              const historyResponse = await apiClient.getUserLoginHistory(user.id, 20)

              if (historyResponse.data) {
                const historyWithUsername = historyResponse.data.map(log => ({
                  ...log,
                  username: user.username
                }))
                allHistory.push(...historyWithUsername)
              }
            } catch (err) {
              console.error(`Failed to load login history for user ${user.id}:`, err)
            }
          }
        }

        // 按时间排序
        allHistory.sort((a, b) =>
          new Date(b.login_at).getTime() - new Date(a.login_at).getTime()
        )

        setLoginHistory(allHistory)
      }
    } catch (err: any) {
      setError(err.message || '加载日志失败')
      console.error('Failed to load logs:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getActionTypeBadge = (actionType: string) => {
    const colors: Record<string, string> = {
      'login': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'logout': 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      'create': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'update': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      'delete': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'backtest': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'sync': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    }

    return (
      <Badge className={colors[actionType] || 'bg-gray-100 text-gray-800'}>
        {actionType}
      </Badge>
    )
  }

  const getStatusBadge = (status: string) => {
    const isSuccess = status === 'success'
    return (
      <Badge className={isSuccess
        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      }>
        {isSuccess ? '成功' : '失败'}
      </Badge>
    )
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const filteredActivityLogs = activityLogs.filter(log => {
    if (searchTerm && log.username && !log.username.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }
    if (userIdFilter && log.user_id !== parseInt(userIdFilter)) {
      return false
    }
    return true
  })

  const filteredLoginHistory = loginHistory.filter(log => {
    if (searchTerm && log.username && !log.username.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }
    if (userIdFilter && log.user_id !== parseInt(userIdFilter)) {
      return false
    }
    return true
  })

  return (
        <div className="space-y-6">
          {/* 页面标题 */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                系统日志
              </h1>
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                查看用户活动和系统操作记录
              </p>
            </div>
            <Button onClick={loadLogs} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          {/* 统计卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  活动日志
                </CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{activityLogs.length}</div>
                <p className="text-xs text-muted-foreground mt-2">
                  最近的用户操作记录
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  登录历史
                </CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{loginHistory.length}</div>
                <p className="text-xs text-muted-foreground mt-2">
                  用户登录记录
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  今日活动
                </CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {activityLogs.filter(log => {
                    const logDate = new Date(log.created_at)
                    const today = new Date()
                    return logDate.toDateString() === today.toDateString()
                  }).length}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  今天的操作记录
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 过滤器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <label className="text-sm font-medium mb-2 block">搜索用户</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="输入用户名搜索..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                {activeTab === 'activity' && (
                  <div className="w-48">
                    <label className="text-sm font-medium mb-2 block">操作类型</label>
                    <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择操作类型" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部</SelectItem>
                        <SelectItem value="login">登录</SelectItem>
                        <SelectItem value="logout">登出</SelectItem>
                        <SelectItem value="create">创建</SelectItem>
                        <SelectItem value="update">更新</SelectItem>
                        <SelectItem value="delete">删除</SelectItem>
                        <SelectItem value="backtest">回测</SelectItem>
                        <SelectItem value="sync">同步</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <Button variant="outline" onClick={() => {
                  setSearchTerm('')
                  setActionTypeFilter('all')
                  setUserIdFilter('')
                }}>
                  <Filter className="h-4 w-4 mr-2" />
                  清除过滤
                </Button>
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
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'activity' | 'login')}>
                <TabsList className="mb-4">
                  <TabsTrigger value="activity">活动日志</TabsTrigger>
                  <TabsTrigger value="login">登录历史</TabsTrigger>
                </TabsList>

                <TabsContent value="activity">
                  {isLoading ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
                      <p className="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
                    </div>
                  ) : error ? (
                    <div className="text-center py-8 text-red-600">{error}</div>
                  ) : filteredActivityLogs.length === 0 ? (
                    <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                      暂无活动日志
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>时间</TableHead>
                            <TableHead>用户</TableHead>
                            <TableHead>操作类型</TableHead>
                            <TableHead>资源类型</TableHead>
                            <TableHead>资源ID</TableHead>
                            <TableHead>IP地址</TableHead>
                            <TableHead>详情</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {filteredActivityLogs.map((log) => (
                            <TableRow key={log.id}>
                              <TableCell className="text-sm">
                                {formatDate(log.created_at)}
                              </TableCell>
                              <TableCell className="font-medium">
                                {log.username || `用户#${log.user_id}`}
                              </TableCell>
                              <TableCell>
                                {getActionTypeBadge(log.action_type)}
                              </TableCell>
                              <TableCell className="text-sm">
                                {log.resource_type || '-'}
                              </TableCell>
                              <TableCell className="text-sm">
                                {log.resource_id || '-'}
                              </TableCell>
                              <TableCell className="text-sm font-mono">
                                {log.ip_address || '-'}
                              </TableCell>
                              <TableCell className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                                {log.details ? JSON.stringify(log.details) : '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="login">
                  {isLoading ? (
                    <div className="text-center py-8">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
                      <p className="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
                    </div>
                  ) : error ? (
                    <div className="text-center py-8 text-red-600">{error}</div>
                  ) : filteredLoginHistory.length === 0 ? (
                    <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                      暂无登录历史
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>登录时间</TableHead>
                            <TableHead>用户</TableHead>
                            <TableHead>状态</TableHead>
                            <TableHead>IP地址</TableHead>
                            <TableHead>浏览器/设备</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {filteredLoginHistory.map((log) => (
                            <TableRow key={log.id}>
                              <TableCell className="text-sm">
                                {formatDate(log.login_at)}
                              </TableCell>
                              <TableCell className="font-medium">
                                {log.username || `用户#${log.user_id}`}
                              </TableCell>
                              <TableCell>
                                {getStatusBadge(log.status)}
                              </TableCell>
                              <TableCell className="text-sm font-mono">
                                {log.ip_address || '-'}
                              </TableCell>
                              <TableCell className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                                {log.user_agent || '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
  )
}
