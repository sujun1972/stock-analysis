/**
 * 我的策略页面
 * 显示用户创建的所有策略及其发布状态
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Plus,
  Edit,
  Code,
  Trash2,
  Send,
  RotateCcw,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'

export default function MyStrategiesPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>('all')

  useEffect(() => {
    loadMyStrategies()
  }, [])

  const loadMyStrategies = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getMyStrategies()
      if (response.data) {
        setStrategies(response.data)
      }
    } catch (error: any) {
      console.error('Failed to load my strategies:', error)
      toast({
        title: '加载失败',
        description: error.response?.data?.detail || '无法加载我的策略列表',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  // 申请发布
  const handleRequestPublish = async (strategyId: number, strategyName: string) => {
    try {
      const response = await apiClient.requestPublishStrategy(strategyId)
      toast({
        title: '申请成功',
        description: `策略 "${strategyName}" 已提交审核`,
      })
      loadMyStrategies() // 刷新列表
    } catch (error: any) {
      toast({
        title: '申请失败',
        description: error.response?.data?.detail || '提交失败，请稍后重试',
        variant: 'destructive'
      })
    }
  }

  // 撤回申请
  const handleWithdrawPublish = async (strategyId: number, strategyName: string) => {
    try {
      const response = await apiClient.withdrawPublishRequest(strategyId)
      toast({
        title: '撤回成功',
        description: `策略 "${strategyName}" 已撤回发布申请`,
      })
      loadMyStrategies() // 刷新列表
    } catch (error: any) {
      toast({
        title: '撤回失败',
        description: error.response?.data?.detail || '撤回失败，请稍后重试',
        variant: 'destructive'
      })
    }
  }

  // 删除策略
  const handleDelete = async (strategyId: number, strategyName: string) => {
    if (!confirm(`确定要删除策略 "${strategyName}" 吗？此操作不可恢复。`)) {
      return
    }

    try {
      await apiClient.deleteStrategy(strategyId)
      toast({
        title: '删除成功',
        description: `策略 "${strategyName}" 已删除`,
      })
      loadMyStrategies() // 刷新列表
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.response?.data?.detail || '删除失败，请稍后重试',
        variant: 'destructive'
      })
    }
  }

  // 按状态筛选策略
  const filteredStrategies = strategies.filter(strategy => {
    if (activeTab === 'all') return true
    return strategy.publish_status === activeTab
  })

  // 统计各状态数量
  const statusCounts = {
    all: strategies.length,
    draft: strategies.filter(s => s.publish_status === 'draft').length,
    pending_review: strategies.filter(s => s.publish_status === 'pending_review').length,
    approved: strategies.filter(s => s.publish_status === 'approved').length,
    rejected: strategies.filter(s => s.publish_status === 'rejected').length,
  }

  return (
    <div className="container mx-auto py-8 px-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">我的策略</h1>
          <p className="text-muted-foreground mt-2">管理和发布你创建的策略</p>
        </div>
        <Link href="/strategies/create">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            创建新策略
          </Button>
        </Link>
      </div>

      {/* 说明提示 */}
      <Alert className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>发布流程：</strong>草稿状态的策略可以申请发布 → 提交后进入待审核状态 → 管理员审核批准后即可发布到策略中心
        </AlertDescription>
      </Alert>

      {/* 状态标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="all">
            全部 <Badge variant="secondary" className="ml-2">{statusCounts.all}</Badge>
          </TabsTrigger>
          <TabsTrigger value="draft">
            草稿 <Badge variant="secondary" className="ml-2">{statusCounts.draft}</Badge>
          </TabsTrigger>
          <TabsTrigger value="pending_review">
            待审核 <Badge variant="secondary" className="ml-2">{statusCounts.pending_review}</Badge>
          </TabsTrigger>
          <TabsTrigger value="approved">
            已发布 <Badge variant="secondary" className="ml-2">{statusCounts.approved}</Badge>
          </TabsTrigger>
          <TabsTrigger value="rejected">
            已拒绝 <Badge variant="secondary" className="ml-2">{statusCounts.rejected}</Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="text-muted-foreground mt-4">加载中...</p>
            </div>
          ) : filteredStrategies.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">暂无策略</p>
                <Link href="/strategies/create">
                  <Button variant="outline" className="mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    创建第一个策略
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredStrategies.map((strategy) => (
                <Card key={strategy.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-lg">{strategy.display_name}</CardTitle>
                        <CardDescription className="mt-1 text-sm">
                          {strategy.description || '暂无描述'}
                        </CardDescription>
                      </div>
                      <PublishStatusBadge status={strategy.publish_status} />
                    </div>

                    {/* 标签 */}
                    <div className="flex flex-wrap gap-1 mt-2">
                      <Badge variant="outline" className="text-xs">
                        {strategy.source_type === 'ai' ? 'AI生成' : '自定义'}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {strategy.strategy_type === 'entry' ? '入场策略' : '离场策略'}
                      </Badge>
                      {strategy.category && (
                        <Badge variant="outline" className="text-xs">
                          {strategy.category}
                        </Badge>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent>
                    {/* 拒绝原因 */}
                    {strategy.publish_status === 'rejected' && strategy.publish_reject_reason && (
                      <Alert variant="destructive" className="mb-4">
                        <XCircle className="h-4 w-4" />
                        <AlertDescription>
                          <strong>拒绝原因：</strong>{strategy.publish_reject_reason}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* 验证状态 */}
                    <div className="flex items-center gap-2 mb-4 text-sm">
                      <span className="text-muted-foreground">验证状态:</span>
                      <Badge variant={strategy.validation_status === 'passed' ? 'default' : 'secondary'}>
                        {strategy.validation_status === 'passed' ? '已通过' : '未验证'}
                      </Badge>
                      <span className="text-muted-foreground">风险:</span>
                      <Badge variant="outline">{strategy.risk_level}</Badge>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex flex-wrap gap-2">
                      {/* 查看代码 */}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/strategies/${strategy.id}/code`)}
                      >
                        <Code className="w-4 h-4 mr-1" />
                        查看代码
                      </Button>

                      {/* 编辑（仅 draft 和 rejected 可编辑） */}
                      {(strategy.publish_status === 'draft' || strategy.publish_status === 'rejected') && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => router.push(`/strategies/${strategy.id}/edit`)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          编辑
                        </Button>
                      )}

                      {/* 申请发布（仅 draft 和 rejected） */}
                      {(strategy.publish_status === 'draft' || strategy.publish_status === 'rejected') &&
                        strategy.validation_status === 'passed' && (
                          <Button
                            size="sm"
                            onClick={() => handleRequestPublish(strategy.id, strategy.display_name)}
                          >
                            <Send className="w-4 h-4 mr-1" />
                            申请发布
                          </Button>
                        )}

                      {/* 撤回申请（仅 pending_review） */}
                      {strategy.publish_status === 'pending_review' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleWithdrawPublish(strategy.id, strategy.display_name)}
                        >
                          <RotateCcw className="w-4 h-4 mr-1" />
                          撤回申请
                        </Button>
                      )}

                      {/* 删除（仅 draft 和 rejected 可删除） */}
                      {(strategy.publish_status === 'draft' || strategy.publish_status === 'rejected') && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(strategy.id, strategy.display_name)}
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          删除
                        </Button>
                      )}
                    </div>

                    {/* 时间信息 */}
                    <div className="mt-4 pt-4 border-t text-xs text-muted-foreground">
                      <div>创建时间: {new Date(strategy.created_at).toLocaleString('zh-CN')}</div>
                      {strategy.publish_requested_at && (
                        <div>申请时间: {new Date(strategy.publish_requested_at).toLocaleString('zh-CN')}</div>
                      )}
                      {strategy.publish_reviewed_at && (
                        <div>审核时间: {new Date(strategy.publish_reviewed_at).toLocaleString('zh-CN')}</div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
