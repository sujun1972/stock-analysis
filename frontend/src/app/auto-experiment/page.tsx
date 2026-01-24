'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Rocket, Plus, RefreshCw, AlertCircle } from 'lucide-react'
import { useExperimentStore } from '@/store/experimentStore'
import { BatchConfigDialog } from '@/components/auto-experiment/BatchConfigDialog'
import { BatchCard } from '@/components/auto-experiment/BatchCard'
import { useToast } from '@/hooks/use-toast'
import { useRouter } from 'next/navigation'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function AutoExperimentPage() {
  const router = useRouter()
  const { toast } = useToast()

  const {
    batches,
    loading,
    error,
    fetchBatches,
    startBatch,
    cancelBatch,
    deleteBatch,
  } = useExperimentStore()

  const [configDialogOpen, setConfigDialogOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [batchToDelete, setBatchToDelete] = useState<{ id: number; name: string } | null>(null)

  useEffect(() => {
    fetchBatches()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchBatches()
    setRefreshing(false)
  }

  const handleBatchCreated = (batchId: number) => {
    toast({
      title: '创建成功',
      description: `批次 #${batchId} 已创建并启动`,
    })

    // 刷新列表
    fetchBatches()

    // 3秒后跳转到详情页
    setTimeout(() => {
      router.push(`/auto-experiment/batch/${batchId}`)
    }, 2000)
  }

  const handleStartBatch = async (batchId: number) => {
    try {
      await startBatch(batchId, 3)
      toast({
        title: '已启动',
        description: `批次 #${batchId} 正在后台运行`,
      })
      fetchBatches()
    } catch (error: any) {
      toast({
        title: '启动失败',
        description: error.message,
        variant: 'destructive',
      })
    }
  }

  const handleCancelBatch = async (batchId: number) => {
    try {
      await cancelBatch(batchId)
      toast({
        title: '已取消',
        description: `批次 #${batchId} 已取消`,
      })
      fetchBatches()
    } catch (error: any) {
      toast({
        title: '取消失败',
        description: error.message,
        variant: 'destructive',
      })
    }
  }

  const handleDeleteBatch = (batchId: number, batchName: string) => {
    setBatchToDelete({ id: batchId, name: batchName })
  }

  const confirmDeleteBatch = async () => {
    if (!batchToDelete) return

    try {
      await deleteBatch(batchToDelete.id)
      toast({
        title: '已删除',
        description: `批次 "${batchToDelete.name}" 已删除`,
      })
      setBatchToDelete(null)
      fetchBatches()
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.message,
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Rocket className="h-8 w-8" />
            自动化实验系统
          </h1>
          <p className="text-muted-foreground mt-2">
            批量训练AI模型，自动筛选最优策略，效率提升10-50倍
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="lg"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`mr-2 h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>

          <Button size="lg" onClick={() => setConfigDialogOpen(true)}>
            <Plus className="mr-2 h-5 w-5" />
            创建批次
          </Button>
        </div>
      </div>

      {/* 系统说明 */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>快速开始</AlertTitle>
        <AlertDescription>
          点击&ldquo;创建批次&rdquo;按钮，选择预定义模板或自定义参数空间，即可自动批量训练数百个模型。
          系统将自动完成训练、回测、评分和排名，您只需等待结果即可。
        </AlertDescription>
      </Alert>

      {/* 错误提示 */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 批次列表 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">
            实验批次
            {batches.length > 0 && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                共 {batches.length} 个
              </span>
            )}
          </h2>
        </div>

        {loading && batches.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
            加载中...
          </div>
        ) : batches.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed rounded-lg">
            <Rocket className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">还没有实验批次</h3>
            <p className="text-muted-foreground mb-4">
              创建您的第一个批次，开始自动化实验之旅
            </p>
            <Button onClick={() => setConfigDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              创建第一个批次
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {batches.map((batch) => (
              <BatchCard
                key={batch.batch_id}
                batch={batch}
                onStart={() => handleStartBatch(batch.batch_id)}
                onCancel={() => handleCancelBatch(batch.batch_id)}
                onDelete={() => handleDeleteBatch(batch.batch_id, batch.batch_name)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 统计信息 */}
      {batches.length > 0 && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="p-4 border rounded-lg">
            <div className="text-sm text-muted-foreground">总批次数</div>
            <div className="text-2xl font-bold">{batches.length}</div>
          </div>
          <div className="p-4 border rounded-lg">
            <div className="text-sm text-muted-foreground">运行中</div>
            <div className="text-2xl font-bold text-blue-600">
              {batches.filter((b) => b.status === 'running').length}
            </div>
          </div>
          <div className="p-4 border rounded-lg">
            <div className="text-sm text-muted-foreground">已完成</div>
            <div className="text-2xl font-bold text-green-600">
              {batches.filter((b) => b.status === 'completed').length}
            </div>
          </div>
          <div className="p-4 border rounded-lg">
            <div className="text-sm text-muted-foreground">总实验数</div>
            <div className="text-2xl font-bold">
              {batches.reduce((sum, b) => sum + b.total_experiments, 0)}
            </div>
          </div>
        </div>
      )}

      {/* 创建批次对话框 */}
      <BatchConfigDialog
        open={configDialogOpen}
        onOpenChange={setConfigDialogOpen}
        onSuccess={handleBatchCreated}
      />

      {/* 删除确认对话框 */}
      <Dialog open={!!batchToDelete} onOpenChange={() => setBatchToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除批次</DialogTitle>
            <DialogDescription>
              确定要删除批次 <strong>"{batchToDelete?.name}"</strong> (#{batchToDelete?.id}) 吗？
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>警告</AlertTitle>
              <AlertDescription>
                此操作将永久删除该批次的所有实验数据、训练结果和模型文件，且无法恢复。
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchToDelete(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDeleteBatch}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
