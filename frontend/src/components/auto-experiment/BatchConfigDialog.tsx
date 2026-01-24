'use client'

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, FlaskConical, Sparkles, Settings2 } from 'lucide-react'
import { useExperimentStore, fetchTemplates } from '@/store/experimentStore'
import { useToast } from '@/hooks/use-toast'

interface BatchConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (batchId: number) => void
}

export function BatchConfigDialog({ open, onOpenChange, onSuccess }: BatchConfigDialogProps) {
  const { toast } = useToast()
  const createBatch = useExperimentStore((state) => state.createBatch)
  const startBatch = useExperimentStore((state) => state.startBatch)

  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState<any>({})
  const [activeTab, setActiveTab] = useState('template')

  // 模板模式
  const [batchName, setBatchName] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('small_grid')
  const [strategy, setStrategy] = useState('grid')
  const [description, setDescription] = useState('')
  const [maxWorkers, setMaxWorkers] = useState(3)
  const [autoStart, setAutoStart] = useState(true)

  // 自定义模式
  const [customParamSpace, setCustomParamSpace] = useState('')

  useEffect(() => {
    if (open) {
      loadTemplates()
    }
  }, [open])

  const loadTemplates = async () => {
    try {
      const data = await fetchTemplates()
      setTemplates(data)
    } catch (error) {
      console.error('加载模板失败:', error)
    }
  }

  const handleSubmit = async () => {
    // 验证
    if (!batchName.trim()) {
      toast({
        title: '验证失败',
        description: '请输入批次名称',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      let config: any = {
        batch_name: batchName,
        strategy: strategy,
        description: description || undefined,
        config: {
          max_workers: maxWorkers,
          auto_backtest: true,
          save_models: true,
        },
      }

      if (activeTab === 'template') {
        // 使用模板
        config.template = selectedTemplate
      } else {
        // 使用自定义参数空间
        try {
          config.param_space = JSON.parse(customParamSpace)
        } catch (error) {
          toast({
            title: '参数错误',
            description: '参数空间JSON格式不正确',
            variant: 'destructive',
          })
          setLoading(false)
          return
        }
      }

      // 创建批次
      const batchId = await createBatch(config)

      toast({
        title: '创建成功',
        description: `批次 #${batchId} 已创建`,
      })

      // 自动启动
      if (autoStart) {
        await startBatch(batchId, maxWorkers)

        toast({
          title: '已启动',
          description: '批次正在后台运行',
        })
      }

      // 重置表单
      setBatchName('')
      setDescription('')
      setCustomParamSpace('')

      onOpenChange(false)

      if (onSuccess) {
        onSuccess(batchId)
      }
    } catch (error: any) {
      toast({
        title: '创建失败',
        description: error.message,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            创建实验批次
          </DialogTitle>
          <DialogDescription>
            批量训练AI模型，自动筛选最优策略
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 基础配置 */}
          <div className="space-y-2">
            <Label htmlFor="batchName">批次名称 *</Label>
            <Input
              id="batchName"
              placeholder="例如：Grid搜索v1"
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">描述（可选）</Label>
            <Textarea
              id="description"
              placeholder="描述此次实验的目的和预期"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* 参数配置选项卡 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="template">
                <Sparkles className="mr-2 h-4 w-4" />
                快速模板
              </TabsTrigger>
              <TabsTrigger value="custom">
                <Settings2 className="mr-2 h-4 w-4" />
                自定义配置
              </TabsTrigger>
            </TabsList>

            {/* 模板选择 */}
            <TabsContent value="template" className="space-y-4">
              <div className="space-y-2">
                <Label>选择模板</Label>
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(templates).map(([key, template]: [string, any]) => (
                      <SelectItem key={key} value={key}>
                        {template.name} - {template.description}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* 模板预览 */}
              {templates[selectedTemplate] && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">模板详情</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">预计实验数</span>
                      <Badge>{templates[selectedTemplate].estimated_experiments}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">包含股票</span>
                      <span>
                        {templates[selectedTemplate].param_space?.symbols?.length || 0} 只
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">模型类型</span>
                      <span>
                        {templates[selectedTemplate].param_space?.model_types?.join(', ') || '-'}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* 自定义配置 */}
            <TabsContent value="custom" className="space-y-4">
              <div className="space-y-2">
                <Label>参数空间（JSON格式）</Label>
                <Textarea
                  placeholder={`{
  "symbols": ["000001", "600000"],
  "model_types": ["lightgbm"],
  "target_periods": [5, 10],
  ...
}`}
                  value={customParamSpace}
                  onChange={(e) => setCustomParamSpace(e.target.value)}
                  rows={10}
                  className="font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground">
                  请输入有效的JSON格式参数空间定义
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {/* 高级设置 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">高级设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="strategy">参数生成策略</Label>
                  <Select value={strategy} onValueChange={setStrategy}>
                    <SelectTrigger id="strategy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="grid">Grid - 网格搜索（全组合）</SelectItem>
                      <SelectItem value="random">Random - 随机采样</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxWorkers">并行Worker数</Label>
                  <Select value={maxWorkers.toString()} onValueChange={(v) => setMaxWorkers(Number(v))}>
                    <SelectTrigger id="maxWorkers">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 Worker（测试）</SelectItem>
                      <SelectItem value="3">3 Workers（推荐）</SelectItem>
                      <SelectItem value="5">5 Workers</SelectItem>
                      <SelectItem value="10">10 Workers（高性能）</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="autoStart"
                  checked={autoStart}
                  onChange={(e) => setAutoStart(e.target.checked)}
                  className="h-4 w-4"
                />
                <Label htmlFor="autoStart" className="cursor-pointer">
                  创建后立即启动批次
                </Label>
              </div>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {autoStart ? '创建并启动' : '创建批次'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
