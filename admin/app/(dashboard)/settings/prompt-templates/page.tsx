'use client'

/**
 * 提示词模板管理 - 列表页面
 */

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  Copy,
  Trash2,
  Clock,
  CheckCircle2,
} from 'lucide-react'

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
    <div className="container mx-auto py-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">提示词模板管理</h1>
          <p className="text-muted-foreground mt-2">
            管理所有LLM调用的提示词模板，支持版本控制和性能统计
          </p>
        </div>
        <Button onClick={() => router.push('/settings/prompt-templates/new')}>
          <Plus className="h-4 w-4 mr-2" />
          创建模板
        </Button>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">业务类型</label>
              <Select value={businessTypeFilter} onValueChange={setBusinessTypeFilter}>
                <SelectTrigger>
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

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">状态</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
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
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <CardTitle className="text-lg">{template.template_name}</CardTitle>
                      {template.is_default && (
                        <Badge variant="default">默认</Badge>
                      )}
                      {template.is_active ? (
                        <Badge variant="outline" className="text-green-600">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          已启用
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-gray-500">
                          已停用
                        </Badge>
                      )}
                      <Badge variant="secondary">
                        {BUSINESS_TYPE_LABELS[template.business_type]}
                      </Badge>
                    </div>
                    <CardDescription>
                      Key: {template.template_key} | 版本: {template.version}
                    </CardDescription>
                  </div>

                  <div className="flex gap-2">
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
                </div>
              </CardHeader>

              <CardContent>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">使用次数</p>
                    <p className="font-semibold text-lg">{template.usage_count || 0}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">成功率</p>
                    <p className="font-semibold text-lg">
                      {template.success_rate ? `${template.success_rate.toFixed(1)}%` : '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">平均Token</p>
                    <p className="font-semibold text-lg">{template.avg_tokens_used || '-'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">平均耗时</p>
                    <p className="font-semibold text-lg">
                      {template.avg_generation_time
                        ? `${template.avg_generation_time.toFixed(2)}s`
                        : '-'}
                    </p>
                  </div>
                </div>

                {template.description && (
                  <div className="mt-4 p-3 bg-muted/50 rounded-md">
                    <p className="text-sm text-muted-foreground">{template.description}</p>
                  </div>
                )}

                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    创建于 {new Date(template.created_at).toLocaleString('zh-CN')}
                  </div>
                  {template.created_by && <div>创建人: {template.created_by}</div>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
