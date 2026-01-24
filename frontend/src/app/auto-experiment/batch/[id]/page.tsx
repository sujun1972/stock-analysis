'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, TrendingUp, BarChart3, Settings2, FileText } from 'lucide-react'
import { useExperimentStore, TopModel } from '@/store/experimentStore'
import { BatchMonitor } from '@/components/auto-experiment/BatchMonitor'

export default function BatchDetailPage() {
  const params = useParams()
  const router = useRouter()
  const batchId = Number(params.id)

  const { currentBatch, topModels, fetchBatchInfo, fetchTopModels } = useExperimentStore()
  const [activeTab, setActiveTab] = useState('monitor')

  useEffect(() => {
    if (batchId) {
      fetchBatchInfo(batchId)
      fetchTopModels(batchId, 20)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId])

  if (!currentBatch) {
    return <div className="container mx-auto p-6">加载中...</div>
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页头 */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            {currentBatch.batch_name}
            <Badge variant={currentBatch.status === 'completed' ? 'success' as any : 'default'}>
              {currentBatch.status}
            </Badge>
          </h1>
          <p className="text-muted-foreground mt-1">
            批次 #{batchId} · {currentBatch.strategy === 'grid' ? '网格搜索' : '随机采样'}
          </p>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>总实验数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{currentBatch.total_experiments}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>已完成</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {currentBatch.completed_experiments}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>成功率</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {currentBatch.success_rate_pct.toFixed(0)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>最高评分</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">
              {currentBatch.max_rank_score?.toFixed(2) || '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 详情标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="monitor">
            <BarChart3 className="mr-2 h-4 w-4" />
            实时监控
          </TabsTrigger>
          <TabsTrigger value="top-models">
            <TrendingUp className="mr-2 h-4 w-4" />
            Top模型
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings2 className="mr-2 h-4 w-4" />
            配置详情
          </TabsTrigger>
          <TabsTrigger value="report">
            <FileText className="mr-2 h-4 w-4" />
            实验报告
          </TabsTrigger>
        </TabsList>

        {/* 实时监控 */}
        <TabsContent value="monitor" className="space-y-4">
          <BatchMonitor batchId={batchId} autoRefresh={true} />
        </TabsContent>

        {/* Top模型 */}
        <TabsContent value="top-models" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top 20 模型</CardTitle>
              <CardDescription>
                按综合评分排序的最优模型
              </CardDescription>
            </CardHeader>
            <CardContent>
              {topModels.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  暂无完成的模型
                </div>
              ) : (
                <div className="space-y-3">
                  {topModels.map((model, index) => (
                    <div
                      key={model.experiment_id}
                      className="p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground font-bold">
                            {index + 1}
                          </div>
                          <div>
                            <div className="font-mono text-sm font-medium">
                              {model.model_id}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {model.config?.symbol} · {model.config?.model_type} ·
                              T{model.config?.target_period}
                            </div>
                          </div>
                        </div>
                        <Badge variant="outline">
                          评分: {model.rank_score?.toFixed(2) || '-'}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">年化收益</div>
                          <div className="font-bold text-green-600">
                            {model.annual_return?.toFixed(2)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">夏普比率</div>
                          <div className="font-bold">
                            {model.sharpe_ratio?.toFixed(2)}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">最大回撤</div>
                          <div className="font-bold text-red-600">
                            {model.max_drawdown?.toFixed(2)}%
                          </div>
                        </div>
                        <div>
                          <Button size="sm" variant="outline" className="w-full">
                            查看详情
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 配置详情 */}
        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>批次配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-muted-foreground">批次名称</div>
                  <div className="font-medium">{currentBatch.batch_name}</div>
                </div>

                {currentBatch.description && (
                  <div>
                    <div className="text-sm text-muted-foreground">描述</div>
                    <div className="font-medium">{currentBatch.description}</div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">策略</div>
                    <div className="font-medium">
                      {currentBatch.strategy === 'grid' ? '网格搜索' : '随机采样'}
                    </div>
                  </div>

                  <div>
                    <div className="text-sm text-muted-foreground">创建时间</div>
                    <div className="font-medium">
                      {new Date(currentBatch.created_at).toLocaleString('zh-CN')}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 实验报告 */}
        <TabsContent value="report" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>实验报告</CardTitle>
              <CardDescription>
                详细的性能分析和参数重要性
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                报告功能开发中...
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
