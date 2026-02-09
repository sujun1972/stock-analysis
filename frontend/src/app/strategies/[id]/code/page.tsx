/**
 * 策略代码查看页面 (V2.0)
 * 展示策略的完整 Python 源代码、参数和元信息
 */

'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { useTheme } from 'next-themes'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Code,
  Copy,
  Download,
  Play,
  ArrowLeft,
  Building2,
  Sparkles,
  User,
  CheckCircle,
  XCircle,
  AlertCircle,
  Edit,
  Trash2,
  Loader2
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'

// 动态导入 Monaco Editor (客户端组件)
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] flex items-center justify-center border rounded-lg bg-muted">
      <Loader2 className="h-8 w-8 animate-spin" />
    </div>
  )
})

export default function StrategyCodePage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const { theme } = useTheme()
  const strategyId = parseInt(params.id as string)

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStrategy()
  }, [strategyId])

  const loadStrategy = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getStrategy(strategyId)
      if (response.data) {
        setStrategy(response.data)
      }
    } catch (error) {
      console.error('Failed to load strategy:', error)
      toast({
        title: '加载失败',
        description: '无法加载策略详情',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  // 复制代码
  const handleCopyCode = () => {
    if (strategy?.code) {
      navigator.clipboard.writeText(strategy.code)
      toast({
        title: '复制成功',
        description: '代码已复制到剪贴板'
      })
    }
  }

  // 下载代码
  const handleDownload = () => {
    if (!strategy) return

    const blob = new Blob([strategy.code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${strategy.name}.py`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: '下载成功',
      description: '代码文件已下载'
    })
  }

  // 删除策略
  const handleDelete = async () => {
    if (!strategy || strategy.source_type === 'builtin') {
      toast({
        title: '操作失败',
        description: '内置策略不允许删除',
        variant: 'destructive'
      })
      return
    }

    if (!confirm('确定要删除这个策略吗？此操作不可恢复。')) {
      return
    }

    try {
      await apiClient.deleteStrategy(strategyId)
      toast({
        title: '删除成功',
        description: '策略已被删除'
      })
      router.push('/strategies')
    } catch (error) {
      console.error('Failed to delete strategy:', error)
      toast({
        title: '删除失败',
        description: '无法删除策略',
        variant: 'destructive'
      })
    }
  }

  // 获取来源图标
  const getSourceIcon = () => {
    if (!strategy) return null
    switch (strategy.source_type) {
      case 'builtin':
        return <Building2 className="h-5 w-5" />
      case 'ai':
        return <Sparkles className="h-5 w-5" />
      case 'custom':
        return <User className="h-5 w-5" />
    }
  }

  // 获取验证状态徽章
  const getValidationBadge = () => {
    if (!strategy) return null

    const variants = {
      passed: { variant: 'default' as const, icon: CheckCircle, label: '已验证' },
      failed: { variant: 'destructive' as const, icon: XCircle, label: '验证失败' },
      pending: { variant: 'secondary' as const, icon: AlertCircle, label: '待验证' },
      validating: { variant: 'outline' as const, icon: AlertCircle, label: '验证中' }
    }

    const info = variants[strategy.validation_status]
    if (!info) return null

    const Icon = info.icon

    return (
      <Badge variant={info.variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {info.label}
      </Badge>
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
            <p className="mt-4 text-muted-foreground">加载中...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!strategy) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Code className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">策略不存在</h3>
              <p className="text-muted-foreground mb-6">
                找不到该策略，可能已被删除
              </p>
              <Button onClick={() => router.push('/strategies')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                返回策略列表
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* 返回按钮 */}
      <Button
        variant="ghost"
        className="mb-4"
        onClick={() => router.push('/strategies')}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        返回策略列表
      </Button>

      {/* 策略信息卡片 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                {getSourceIcon()}
                <CardTitle className="text-2xl">{strategy.display_name}</CardTitle>
              </div>
              <CardDescription className="text-base">
                {strategy.description || '暂无描述'}
              </CardDescription>
            </div>
            <div className="flex flex-col items-end gap-2">
              {getValidationBadge()}
              <Badge variant="outline">{strategy.category || '未分类'}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">策略标识</p>
              <p className="font-medium">{strategy.name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">类名</p>
              <p className="font-medium font-mono text-sm">{strategy.class_name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">版本</p>
              <p className="font-medium">v{strategy.version}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">使用次数</p>
              <p className="font-medium">{strategy.usage_count}</p>
            </div>
          </div>

          {/* 标签 */}
          {strategy.tags && strategy.tags.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-muted-foreground mb-2">标签</p>
              <div className="flex flex-wrap gap-2">
                {strategy.tags.map((tag, index) => (
                  <Badge key={index} variant="outline">{tag}</Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab 内容 */}
      <Tabs defaultValue="code">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="code">策略代码</TabsTrigger>
          <TabsTrigger value="params">默认参数</TabsTrigger>
          <TabsTrigger value="info">元信息</TabsTrigger>
        </TabsList>

        {/* 代码 Tab */}
        <TabsContent value="code">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Python 源代码</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/strategies/create?mode=ai')}
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    AI生成
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleCopyCode}>
                    <Copy className="mr-2 h-4 w-4" />
                    复制
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownload}>
                    <Download className="mr-2 h-4 w-4" />
                    下载
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg overflow-hidden border">
                <Editor
                  height="600px"
                  defaultLanguage="python"
                  value={strategy.code}
                  theme={theme === 'dark' ? 'vs-dark' : 'light'}
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    fontSize: 14,
                    lineNumbers: 'on',
                    rulers: [80, 120],
                    wordWrap: 'on',
                    scrollBeyondLastLine: false,
                    folding: true,
                    renderWhitespace: 'selection',
                    contextmenu: true,
                    selectOnLineNumbers: true
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 参数 Tab */}
        <TabsContent value="params">
          <Card>
            <CardHeader>
              <CardTitle>默认参数配置</CardTitle>
              <CardDescription>
                这些参数会在创建策略实例时使用
              </CardDescription>
            </CardHeader>
            <CardContent>
              {strategy.default_params ? (
                <pre className="bg-muted p-4 rounded-lg overflow-auto">
                  {JSON.stringify(strategy.default_params, null, 2)}
                </pre>
              ) : (
                <p className="text-muted-foreground">暂无默认参数</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 元信息 Tab */}
        <TabsContent value="info">
          <Card>
            <CardHeader>
              <CardTitle>策略元信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">来源类型</p>
                  <Badge variant="outline">{strategy.source_type}</Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">风险等级</p>
                  <Badge>{strategy.risk_level}</Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">启用状态</p>
                  <Badge variant={strategy.is_enabled ? 'default' : 'secondary'}>
                    {strategy.is_enabled ? '已启用' : '已禁用'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">回测次数</p>
                  <p className="font-medium">{strategy.backtest_count || 0}</p>
                </div>
              </div>

              {/* 性能指标 */}
              {(strategy.avg_sharpe_ratio || strategy.avg_annual_return) && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">平均表现</p>
                  <div className="grid grid-cols-2 gap-4">
                    {strategy.avg_sharpe_ratio && (
                      <div>
                        <p className="text-sm text-muted-foreground">夏普率</p>
                        <p className="text-xl font-bold">{strategy.avg_sharpe_ratio.toFixed(2)}</p>
                      </div>
                    )}
                    {strategy.avg_annual_return && (
                      <div>
                        <p className="text-sm text-muted-foreground">年化收益</p>
                        <p className="text-xl font-bold">
                          {(strategy.avg_annual_return * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 时间信息 */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">创建时间:</span>
                  <span>{new Date(strategy.created_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">更新时间:</span>
                  <span>{new Date(strategy.updated_at).toLocaleString()}</span>
                </div>
                {strategy.last_used_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">最后使用:</span>
                    <span>{new Date(strategy.last_used_at).toLocaleString()}</span>
                  </div>
                )}
                {strategy.created_by && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">创建者:</span>
                    <span>{strategy.created_by}</span>
                  </div>
                )}
              </div>

              {/* 代码哈希 */}
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">代码哈希 (SHA256)</p>
                <p className="font-mono text-xs bg-muted p-2 rounded break-all">
                  {strategy.code_hash}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 操作按钮 */}
      <Card className="mt-6">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Button
              className="flex-1"
              onClick={() => router.push(`/backtest?type=unified&id=${strategy.id}`)}
            >
              <Play className="mr-2 h-4 w-4" />
              使用此策略进行回测
            </Button>

            <Button
              variant="outline"
              onClick={() => router.push(`/strategies/create?clone=${strategy.id}`)}
            >
              <Copy className="mr-2 h-4 w-4" />
              创建变体
            </Button>

            {strategy.source_type !== 'builtin' && (
              <>
                <Button
                  variant="outline"
                  onClick={() => router.push(`/strategies/${strategy.id}/edit`)}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  编辑
                </Button>

                <Button
                  variant="destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
