'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import AdminLayout from '@/components/layouts/AdminLayout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Save, RefreshCw } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import type { Concept, StockInfo } from '@/types/stock'

export default function StockConceptsPage() {
  const params = useParams()
  const router = useRouter()
  const code = params.code as string

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [stockConcepts, setStockConcepts] = useState<Concept[]>([])
  const [allConcepts, setAllConcepts] = useState<Concept[]>([])
  const [selectedConceptIds, setSelectedConceptIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // 加载数据
  const loadData = async () => {
    setLoading(true)
    try {
      // 并行加载股票信息、股票概念和所有概念
      const [stockInfoData, conceptsData, allConceptsData] = await Promise.all([
        apiClient.getStock(code),
        apiClient.getStockConcepts(code),
        apiClient.getConceptsList({ limit: 200 })
      ])

      setStockInfo(stockInfoData)
      setStockConcepts(conceptsData)
      setAllConcepts(allConceptsData.items || [])
      setSelectedConceptIds(conceptsData.map(c => c.id))
    } catch (error: any) {
      toast.error('加载数据失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (code) {
      loadData()
    }
  }, [code])

  // 切换概念选择状态
  const toggleConceptSelection = (conceptId: number) => {
    setSelectedConceptIds(prev => {
      if (prev.includes(conceptId)) {
        return prev.filter(id => id !== conceptId)
      } else {
        return [...prev, conceptId]
      }
    })
  }

  // 保存概念标签
  const handleSave = async () => {
    setSaving(true)
    try {
      await apiClient.updateStockConcepts(code, selectedConceptIds)
      toast.success('保存成功')
      // 重新加载数据
      await loadData()
    } catch (error: any) {
      toast.error('保存失败: ' + (error.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  // 重置选择
  const handleReset = () => {
    setSelectedConceptIds(stockConcepts.map(c => c.id))
  }

  // 检查是否有未保存的更改
  const hasChanges = () => {
    const currentIds = [...selectedConceptIds].sort()
    const originalIds = [...stockConcepts.map(c => c.id)].sort()
    return JSON.stringify(currentIds) !== JSON.stringify(originalIds)
  }

  return (
    <ProtectedRoute requireAdmin>
      <AdminLayout>
        <div className="space-y-6">
          {/* 页面标题和导航 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => router.back()}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  {stockInfo?.name || code} - 概念标签分配
                </h1>
                <p className="text-muted-foreground mt-2">
                  为股票分配概念标签，帮助分类和筛选
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={!hasChanges() || saving}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                重置
              </Button>
              <Button
                onClick={handleSave}
                disabled={!hasChanges() || saving}
              >
                <Save className={`mr-2 h-4 w-4 ${saving ? 'animate-spin' : ''}`} />
                保存更改
              </Button>
            </div>
          </div>

          {loading ? (
            <Card>
              <CardContent className="py-12">
                <div className="flex items-center justify-center">
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  加载中...
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* 股票基本信息 */}
              <Card>
                <CardHeader>
                  <CardTitle>股票信息</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">股票代码</p>
                      <p className="text-lg font-medium">{stockInfo?.code}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">股票名称</p>
                      <p className="text-lg font-medium">{stockInfo?.name}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">市场</p>
                      <p className="text-lg font-medium">{stockInfo?.market || '-'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">行业</p>
                      <p className="text-lg font-medium">{stockInfo?.industry || '-'}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 当前已分配的概念 */}
              <Card>
                <CardHeader>
                  <CardTitle>当前概念标签</CardTitle>
                  <CardDescription>
                    已分配 {selectedConceptIds.length} 个概念标签
                    {hasChanges() && (
                      <span className="ml-2 text-orange-600 dark:text-orange-400">
                        (有未保存的更改)
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {selectedConceptIds.length > 0 ? (
                      allConcepts
                        .filter(c => selectedConceptIds.includes(c.id))
                        .map((concept) => (
                          <Badge
                            key={concept.id}
                            variant="default"
                            className="text-sm px-3 py-1"
                          >
                            {concept.name}
                          </Badge>
                        ))
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无概念标签</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* 可选择的概念列表 */}
              <Card>
                <CardHeader>
                  <CardTitle>选择概念标签</CardTitle>
                  <CardDescription>
                    点击概念标签进行选择或取消选择
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[500px] overflow-y-auto border rounded-lg p-4">
                    <div className="flex flex-wrap gap-2">
                      {allConcepts.map((concept) => {
                        const isSelected = selectedConceptIds.includes(concept.id)
                        return (
                          <button
                            key={concept.id}
                            onClick={() => toggleConceptSelection(concept.id)}
                            className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                              isSelected
                                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                          >
                            {concept.name}
                            <span className="ml-2 text-xs opacity-70">
                              ({concept.stock_count})
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 统计信息 */}
              <Card>
                <CardHeader>
                  <CardTitle>统计信息</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold">{allConcepts.length}</p>
                      <p className="text-sm text-muted-foreground">可用概念总数</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold">{selectedConceptIds.length}</p>
                      <p className="text-sm text-muted-foreground">已选择概念</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold">
                        {allConcepts.length - selectedConceptIds.length}
                      </p>
                      <p className="text-sm text-muted-foreground">未选择概念</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </AdminLayout>
    </ProtectedRoute>
  )
}
