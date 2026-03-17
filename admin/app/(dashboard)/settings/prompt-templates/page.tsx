'use client'

/**
 * 提示词模板管理 - 列表页面
 */

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { promptTemplateApi } from '@/lib/prompt-template-api'
import type { PromptTemplate } from '@/types/prompt-template'
import { BUSINESS_TYPE_LABELS } from '@/types/prompt-template'
import {
  FileText,
  Plus,
  Edit,
  Power,
  PowerOff,
  TrendingUp,
  Trash2,
  Clock,
  CheckCircle2,
  MoreVertical,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export default function PromptTemplatesPage() {
  const router = useRouter()
  const { toast } = useToast()

  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [businessTypeFilter, setBusinessTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // 加载模板列表
  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (businessTypeFilter !== 'all') {
        params.business_type = businessTypeFilter
      }
      if (statusFilter === 'active') {
        params.is_active = true
      } else if (statusFilter === 'inactive') {
        params.is_active = false
      }

      const response = await promptTemplateApi.list(params)
      setTemplates(response.items)
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载提示词模板列表',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }, [businessTypeFilter, statusFilter, toast])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  // 激活模板
  const handleActivate = async (id: number, setAsDefault: boolean = false) => {
    try {
      await promptTemplateApi.activate(id, setAsDefault)
      toast({
        title: '操作成功',
        description: setAsDefault ? '已激活并设为默认模板' : '已激活模板',
      })
      loadTemplates()
    } catch (error: any) {
      toast({
        title: '操作失败',
        description: error.response?.data?.detail || '无法激活模板',
        variant: 'destructive',
      })
    }
  }

  // 停用模板
  const handleDeactivate = async (id: number) => {
    try {
      await promptTemplateApi.deactivate(id)
      toast({
        title: '操作成功',
        description: '已停用模板',
      })
      loadTemplates()
    } catch (error: any) {
      toast({
        title: '操作失败',
        description: error.response?.data?.detail || '无法停用模板',
        variant: 'destructive',
      })
    }
  }

  // 删除模板
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除此模板吗？此操作不可撤销。')) {
      return
    }

    try {
      await promptTemplateApi.delete(id)
      toast({
        title: '删除成功',
        description: '模板已删除',
      })
      loadTemplates()
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.response?.data?.detail || '无法删除模板',
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="提示词模板管理"
        description="管理所有LLM调用的提示词模板，支持版本控制和性能统计"
        actions={
          <Button onClick={() => router.push('/settings/prompt-templates/new')}>
            <Plus className="h-4 w-4 mr-2" />
            创建模板
          </Button>
        }
      />

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base sm:text-lg">筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="w-full">
              <label className="text-sm font-medium mb-2 block">业务类型</label>
              <Select value={businessTypeFilter} onValueChange={setBusinessTypeFilter}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="sentiment_analysis">市场情绪分析</SelectItem>
                  <SelectItem value="premarket_analysis">盘前预期分析</SelectItem>
                  <SelectItem value="strategy_generation">策略生成</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="w-full">
              <label className="text-sm font-medium mb-2 block">状态</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="active">已启用</SelectItem>
                  <SelectItem value="inactive">已停用</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 模板列表 */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">加载中...</p>
        </div>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">暂无模板数据</p>
            <Button className="mt-4" onClick={() => router.push('/settings/prompt-templates/new')}>
              创建第一个模板
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {templates.map((template) => (
            <Card key={template.id} className={template.is_default ? 'border-primary' : ''}>
              <CardHeader className="pb-3">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <CardTitle className="text-base sm:text-lg break-all">{template.template_name}</CardTitle>
                      {template.is_default && (
                        <Badge variant="default" className="text-xs">默认</Badge>
                      )}
                      {template.is_active ? (
                        <Badge variant="outline" className="text-green-600 text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          已启用
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-gray-500 text-xs">
                          已停用
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        {BUSINESS_TYPE_LABELS[template.business_type]}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs sm:text-sm">
                      <span className="block sm:inline">Key: {template.template_key}</span>
                      <span className="hidden sm:inline"> | </span>
                      <span className="block sm:inline">版本: {template.version}</span>
                    </CardDescription>
                  </div>

                  {/* 桌面端按钮组 */}
                  <div className="hidden sm:flex gap-2 flex-wrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/settings/prompt-templates/${template.id}`)}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      编辑
                    </Button>

                    {template.is_active ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeactivate(template.id)}
                      >
                        <PowerOff className="h-4 w-4 mr-1" />
                        停用
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleActivate(template.id)}
                      >
                        <Power className="h-4 w-4 mr-1" />
                        启用
                      </Button>
                    )}

                    {!template.is_default && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleActivate(template.id, true)}
                      >
                        设为默认
                      </Button>
                    )}

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        router.push(`/settings/prompt-templates/${template.id}/statistics`)
                      }
                    >
                      <TrendingUp className="h-4 w-4 mr-1" />
                      统计
                    </Button>

                    {!template.is_default && !template.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(template.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    )}
                  </div>

                  {/* 移动端下拉菜单 */}
                  <div className="sm:hidden">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreVertical className="h-4 w-4" />
                          <span className="sr-only">操作菜单</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem
                          onClick={() => router.push(`/settings/prompt-templates/${template.id}`)}
                        >
                          <Edit className="mr-2 h-4 w-4" />
                          编辑模板
                        </DropdownMenuItem>

                        {template.is_active ? (
                          <DropdownMenuItem onClick={() => handleDeactivate(template.id)}>
                            <PowerOff className="mr-2 h-4 w-4" />
                            停用模板
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => handleActivate(template.id)}>
                            <Power className="mr-2 h-4 w-4" />
                            启用模板
                          </DropdownMenuItem>
                        )}

                        {!template.is_default && (
                          <DropdownMenuItem onClick={() => handleActivate(template.id, true)}>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            设为默认
                          </DropdownMenuItem>
                        )}

                        <DropdownMenuItem
                          onClick={() => router.push(`/settings/prompt-templates/${template.id}/statistics`)}
                        >
                          <TrendingUp className="mr-2 h-4 w-4" />
                          查看统计
                        </DropdownMenuItem>

                        {!template.is_default && !template.is_active && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleDelete(template.id)}
                              className="text-red-600 focus:text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除模板
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 text-xs sm:text-sm">
                  <div className="bg-muted/30 rounded-lg p-2 sm:p-3">
                    <p className="text-muted-foreground text-xs">使用次数</p>
                    <p className="font-semibold text-base sm:text-lg mt-1">{template.usage_count || 0}</p>
                  </div>
                  <div className="bg-muted/30 rounded-lg p-2 sm:p-3">
                    <p className="text-muted-foreground text-xs">成功率</p>
                    <p className="font-semibold text-base sm:text-lg mt-1">
                      {template.success_rate ? `${template.success_rate.toFixed(1)}%` : '-'}
                    </p>
                  </div>
                  <div className="bg-muted/30 rounded-lg p-2 sm:p-3">
                    <p className="text-muted-foreground text-xs">平均Token</p>
                    <p className="font-semibold text-base sm:text-lg mt-1">{template.avg_tokens_used || '-'}</p>
                  </div>
                  <div className="bg-muted/30 rounded-lg p-2 sm:p-3">
                    <p className="text-muted-foreground text-xs">平均耗时</p>
                    <p className="font-semibold text-base sm:text-lg mt-1">
                      {template.avg_generation_time
                        ? `${template.avg_generation_time.toFixed(2)}s`
                        : '-'}
                    </p>
                  </div>
                </div>

                {template.description && (
                  <div className="mt-3 sm:mt-4 p-2 sm:p-3 bg-muted/50 rounded-md">
                    <p className="text-xs sm:text-sm text-muted-foreground">{template.description}</p>
                  </div>
                )}

                <div className="mt-3 sm:mt-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3 flex-shrink-0" />
                    <span>创建于 {new Date(template.created_at).toLocaleString('zh-CN', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}</span>
                  </div>
                  {template.created_by && (
                    <div className="flex items-center gap-1">
                      <span>创建人: {template.created_by}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
