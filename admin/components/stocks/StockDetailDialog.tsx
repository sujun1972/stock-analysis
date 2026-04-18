'use client'

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { X, Plus, Trash2, Save, Loader2, Tag } from 'lucide-react'
import { axiosInstance } from '@/lib/api'
import logger from '@/lib/logger'
import type { StockInfo, Concept } from '@/types/stock'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { SimpleConceptSelect } from './SimpleConceptSelect'

interface StockDetailDialogProps {
  stock: StockInfo | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdate?: () => void
}

export function StockDetailDialog({
  stock,
  open,
  onOpenChange,
  onUpdate,
}: StockDetailDialogProps) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // 股票的概念列表
  const [stockConcepts, setStockConcepts] = useState<Concept[]>([])

  // 选中要添加的概念
  const [selectedConceptId, setSelectedConceptId] = useState<string>('')

  // 加载股票的概念
  const loadStockConcepts = useCallback(async () => {
    if (!stock?.code) return

    setLoading(true)
    try {
      const response = await axiosInstance.get(`/api/concepts/stock/${stock.code}`) as any
      setStockConcepts(response.data || [])
    } catch (error: any) {
      logger.error('加载股票概念失败', error)
      toast.error('加载股票概念失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [stock?.code])

  // 远程搜索概念（支持后端分页和搜索）
  const handleSearchConcepts = async (query: string): Promise<Concept[]> => {
    try {
      const response = await axiosInstance.get('/api/concepts/list', {
        params: { search: query, page: 1, page_size: 50 },
      }) as any
      const data = response.data || { items: [] }
      return data.items || []
    } catch (error: any) {
      logger.error('搜索概念失败', error)
      return []
    }
  }

  // 获取选中概念的详情（用于显示已选中的概念）
  const handleFetchSelectedConcept = async (conceptId: string): Promise<Concept | null> => {
    try {
      const id = Number(conceptId)
      const response = await axiosInstance.get(`/api/concepts/${id}`) as any
      return response.data
    } catch (error: any) {
      logger.error('获取概念详情失败', error)
      return null
    }
  }

  // 添加概念
  const handleAddConcept = async () => {
    if (!selectedConceptId) {
      toast.warning('请选择要添加的概念')
      return
    }

    // 检查是否已存在
    const conceptId = Number(selectedConceptId)
    if (stockConcepts.some(c => c.id === conceptId)) {
      toast.warning('该概念已存在')
      return
    }

    // 从后端获取概念详情
    const concept = await handleFetchSelectedConcept(selectedConceptId)
    if (!concept) {
      toast.error('获取概念详情失败')
      return
    }

    setStockConcepts([...stockConcepts, concept])
    setSelectedConceptId('')
    toast.success(`已添加概念: ${concept.name}`)
  }

  // 删除概念
  const handleRemoveConcept = (conceptId: number) => {
    const concept = stockConcepts.find(c => c.id === conceptId)
    setStockConcepts(stockConcepts.filter(c => c.id !== conceptId))
    if (concept) {
      toast.success(`已移除概念: ${concept.name}`)
    }
  }

  // 保存概念更改
  const handleSaveConcepts = async () => {
    if (!stock?.code) return

    setSaving(true)
    try {
      const conceptIds = stockConcepts.map(c => c.id)
      await axiosInstance.put(`/api/concepts/stock/${stock.code}/concepts`, conceptIds)
      toast.success('概念更新成功')
      onUpdate?.()
    } catch (error: any) {
      toast.error('更新概念失败: ' + (error.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  // 当弹窗打开时加载数据
  useEffect(() => {
    if (open && stock) {
      loadStockConcepts()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, stock, loadStockConcepts])

  if (!stock) return null

  // 处理 Dialog 关闭，防止点击下拉框时关闭
  const handleOpenChange = (newOpen: boolean) => {
    // 如果要关闭 Dialog，检查是否是因为点击了概念选择下拉框
    if (!newOpen) {
      const dropdown = document.querySelector('[data-concept-select-dropdown]')
      if (dropdown) {
        // 下拉框打开时，不关闭 Dialog
        return
      }
    }
    onOpenChange(newOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-2xl max-h-[80vh] overflow-y-auto"
        onEscapeKeyDown={(e) => {
          // 如果下拉框打开，按ESC只关闭下拉框，不关闭Dialog
          const dropdown = document.querySelector('[data-concept-select-dropdown]')
          if (dropdown) {
            e.preventDefault()
          }
        }}
        onInteractOutside={(e) => {
          // 如果点击的是概念选择下拉框，不关闭 Dialog
          const target = e.target as HTMLElement
          const dropdown = target.closest('[data-concept-select-dropdown]')
          if (dropdown) {
            e.preventDefault()
          }
        }}
        onFocusOutside={(e) => {
          // 如果焦点移到概念选择下拉框，允许焦点离开 Dialog
          const target = e.target as HTMLElement
          const dropdown = target.closest('[data-concept-select-dropdown]')
          if (dropdown) {
            e.preventDefault()
          }
        }}
      >
        <DialogHeader>
          <DialogTitle className="text-2xl">股票详情</DialogTitle>
          <DialogDescription>
            查看和编辑股票的基本信息和概念标签
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 overflow-visible">
          {/* 基本信息 */}
          <div>
            <h3 className="text-lg font-semibold mb-3">基本信息</h3>
            <div className="grid grid-cols-2 gap-4 bg-muted/50 p-4 rounded-lg">
              <div>
                <Label className="text-muted-foreground">股票代码</Label>
                <p className="font-mono font-semibold">{stock.code}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">股票名称</Label>
                <p className="font-semibold">{stock.name}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">市场</Label>
                <div>
                  <Badge variant="outline">{stock.market}</Badge>
                </div>
              </div>
              <div>
                <Label className="text-muted-foreground">状态</Label>
                <div>
                  {stock.status === 'L' && <Badge variant="default">正常上市</Badge>}
                  {stock.status === 'D' && <Badge variant="destructive">退市</Badge>}
                  {stock.status === 'P' && <Badge variant="secondary">暂停上市</Badge>}
                  {!stock.status && <Badge variant="outline">未知</Badge>}
                </div>
              </div>
              {stock.industry && (
                <div>
                  <Label className="text-muted-foreground">行业</Label>
                  <p>{stock.industry}</p>
                </div>
              )}
              {stock.area && (
                <div>
                  <Label className="text-muted-foreground">地区</Label>
                  <p>{stock.area}</p>
                </div>
              )}
              {stock.list_date && (
                <div>
                  <Label className="text-muted-foreground">上市日期</Label>
                  <p>{stock.list_date}</p>
                </div>
              )}
            </div>
          </div>

          {/* 实时行情 */}
          {stock.latest_price && (
            <div>
              <h3 className="text-lg font-semibold mb-3">实时行情</h3>
              <div className="grid grid-cols-3 gap-4 bg-muted/50 p-4 rounded-lg">
                <div>
                  <Label className="text-muted-foreground">最新价</Label>
                  <p className="text-lg font-semibold">
                    {stock.latest_price?.toFixed(2) || '-'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">涨跌幅</Label>
                  <p className={`text-lg font-semibold ${
                    stock.pct_change && stock.pct_change > 0 ? 'text-red-600' :
                    stock.pct_change && stock.pct_change < 0 ? 'text-green-600' :
                    'text-gray-500'
                  }`}>
                    {stock.pct_change !== undefined && stock.pct_change !== null
                      ? `${stock.pct_change > 0 ? '+' : ''}${stock.pct_change.toFixed(2)}%`
                      : '-'
                    }
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">换手率</Label>
                  <p className="text-lg font-semibold">
                    {stock.turnover !== undefined && stock.turnover !== null
                      ? `${stock.turnover.toFixed(2)}%`
                      : '-'
                    }
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">成交量</Label>
                  <p className="text-sm">
                    {stock.volume
                      ? `${(stock.volume / 10000).toFixed(2)} 万手`
                      : '-'
                    }
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">成交额</Label>
                  <p className="text-sm">
                    {stock.amount
                      ? `${(stock.amount / 100000000).toFixed(2)} 亿`
                      : '-'
                    }
                  </p>
                </div>
                {stock.trade_time && (
                  <div>
                    <Label className="text-muted-foreground">更新时间</Label>
                    <p className="text-sm">{stock.trade_time}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <Separator />

          {/* 概念标签编辑 */}
          <div className="overflow-visible">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Tag className="h-5 w-5" />
                概念标签
              </h3>
              <Button
                onClick={handleSaveConcepts}
                disabled={saving}
                size="sm"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    保存修改
                  </>
                )}
              </Button>
            </div>

            {/* 添加概念 */}
            <div className="flex gap-2 mb-4 overflow-visible">
              <div className="flex-1 overflow-visible">
                <SimpleConceptSelect
                  value={selectedConceptId}
                  onSelect={setSelectedConceptId}
                  placeholder="搜索并选择概念..."
                  disabled={false}
                  valueType="id"
                  remoteSearch={true}
                  onSearch={handleSearchConcepts}
                  onFetchSelected={handleFetchSelectedConcept}
                />
              </div>
              <Button
                onClick={handleAddConcept}
                disabled={!selectedConceptId}
                variant="outline"
              >
                <Plus className="h-4 w-4 mr-2" />
                添加
              </Button>
            </div>

            {/* 当前概念列表 */}
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">加载中...</span>
              </div>
            ) : stockConcepts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                暂无概念标签，请添加
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto border rounded-lg p-3">
                {stockConcepts.map((concept) => (
                  <div
                    key={concept.id}
                    className="flex items-center justify-between p-2 bg-muted/50 rounded hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{concept.code}</Badge>
                      <span className="font-medium">{concept.name}</span>
                      {concept.stock_count !== undefined && (
                        <span className="text-sm text-muted-foreground">
                          ({concept.stock_count} 只股票)
                        </span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveConcept(concept.id)}
                      className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
