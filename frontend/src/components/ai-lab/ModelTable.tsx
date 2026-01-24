/**
 * 模型表格组件
 * 以表格形式展示所有训练完成的模型
 */

'use client';

import { useEffect, useState } from 'react';
import { useMLStore } from '@/store/mlStore';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MoreHorizontal, PlayCircle, TrendingUp, Trash2, RefreshCw, Search, Info, Plus } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import TrainingConfigPanel from './TrainingConfigPanel';
import TrainingMonitor from './TrainingMonitor';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function ModelTable() {
  const { models, setModels, setSelectedModel, currentTask } = useMLStore();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<any | null>(null);

  // 筛选和搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  const [modelTypeFilter, setModelTypeFilter] = useState('all');

  // 训练配置弹窗状态
  const [showTrainingDialog, setShowTrainingDialog] = useState(false);

  // 训练进度模态窗口状态
  const [showTrainingMonitor, setShowTrainingMonitor] = useState(false);

  // 加载模型列表
  const loadModels = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/ml/models`, {
        params: { limit: 100 }
      });
      setModels(response.data.models || []);
    } catch (error) {
      console.error('加载模型列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 运行预测
  const handlePredict = (model: any) => {
    setSelectedModel(model);
    router.push(`/ai-lab/prediction?modelId=${model.model_id}`);
  };

  // 查看详情
  const handleViewDetails = (model: any) => {
    setSelectedModel(model);
    router.push(`/ai-lab/model-details?modelId=${model.model_id}`);
  };

  /**
   * 跳转到回测页面并预填参数
   * 使用模型训练时的配置自动设置回测参数，并在页面加载后自动执行回测
   */
  const handleQuickBacktest = (model: any) => {
    // 构建回测配置，使用模型训练时的日期范围
    const config = {
      strategyId: 'ml_model',
      symbols: model.symbol,
      startDate: model.config?.start_date || '2020-01-01',
      endDate: model.config?.end_date || new Date().toISOString().split('T')[0],
      initialCash: 100000,
      strategyParams: {
        model_id: model.model_id,
        buy_threshold: 1.0,
        sell_threshold: -1.0,
        commission: 0.0003,
        slippage: 0.001,
        position_size: 1.0,
        stop_loss: 0.05,
        take_profit: 0.10,
      }
    };

    // 通过 URL 参数传递配置，回测页面将自动执行
    const configParam = encodeURIComponent(JSON.stringify(config));
    router.push(`/backtest?config=${configParam}`);
  };

  // 删除模型
  const handleDeleteClick = (model: any) => {
    setModelToDelete(model);
  };

  const confirmDelete = async () => {
    if (!modelToDelete) return;

    try {
      await axios.delete(`${API_BASE}/ml/tasks/${modelToDelete.model_id}`);

      toast({
        title: '删除成功',
        description: `模型 ${modelToDelete.symbol} 已删除`,
      });

      // 重新加载列表
      loadModels();
      setModelToDelete(null);
    } catch (error: any) {
      console.error('删除模型失败:', error);
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: error.response?.data?.detail || error.message || '未知错误',
      });
    }
  };

  // 监听训练任务状态变化
  useEffect(() => {
    if (currentTask) {
      // 如果有训练任务在运行，显示训练监控窗口
      if (currentTask.status === 'running') {
        setShowTrainingMonitor(true);
      }
      // 如果训练完成，关闭监控窗口，刷新列表，显示成功提示
      else if (currentTask.status === 'completed') {
        setShowTrainingMonitor(false);
        setShowTrainingDialog(false);

        // 静默刷新模型列表
        loadModels();

        // 显示成功提示
        toast({
          title: '训练完成',
          description: `模型 ${currentTask.config?.symbol} - ${currentTask.config?.model_type?.toUpperCase()} 训练成功！`,
        });
      }
      // 如果训练失败，关闭监控窗口
      else if (currentTask.status === 'failed') {
        setShowTrainingMonitor(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTask]);

  // 应用筛选和搜索逻辑
  const filteredModels = models.filter(model => {
    const matchesSearch = model.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = modelTypeFilter === 'all' || model.model_type === modelTypeFilter;
    return matchesSearch && matchesType;
  });

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>模型仓库</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3 text-muted-foreground">加载模型列表...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>模型仓库</CardTitle>
            <div className="flex items-center gap-2">
              {/* 搜索框 */}
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索股票代码..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 w-[200px]"
                />
              </div>

              {/* 模型类型筛选 */}
              <Select value={modelTypeFilter} onValueChange={setModelTypeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="模型类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="lightgbm">LightGBM</SelectItem>
                  <SelectItem value="gru">GRU</SelectItem>
                </SelectContent>
              </Select>

              {/* 刷新按钮 */}
              <Button variant="outline" size="icon" onClick={loadModels} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>

              {/* 训练按钮 */}
              <Button onClick={() => setShowTrainingDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                训练模型
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>股票代码</TableHead>
                  <TableHead>模型类型</TableHead>
                  <TableHead>预测周期</TableHead>
                  <TableHead className="text-right">RMSE</TableHead>
                  <TableHead className="text-right">R²</TableHead>
                  <TableHead className="text-right">IC</TableHead>
                  <TableHead className="text-right">Rank IC</TableHead>
                  <TableHead>训练时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredModels.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                      {models.length === 0 ? '暂无模型数据' : '未找到匹配的模型'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredModels.map((model) => (
                    <TableRow key={model.model_id}>
                      <TableCell className="font-medium">{model.symbol}</TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded ${
                            model.model_type === 'lightgbm'
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                          }`}
                        >
                          {model.model_type.toUpperCase()}
                        </span>
                      </TableCell>
                      <TableCell>{model.target_period}天</TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.metrics?.rmse?.toFixed(4) || 'N/A'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.metrics?.r2?.toFixed(4) || 'N/A'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-blue-600 dark:text-blue-400">
                        {model.metrics?.ic?.toFixed(4) || 'N/A'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-blue-600 dark:text-blue-400">
                        {model.metrics?.rank_ic?.toFixed(4) || 'N/A'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {model.trained_at?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$1-$2-$3') || 'N/A'}
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleViewDetails(model)}>
                              <Info className="mr-2 h-4 w-4" />
                              查看详情
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handlePredict(model)}>
                              <PlayCircle className="mr-2 h-4 w-4" />
                              运行预测
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleQuickBacktest(model)}>
                              <TrendingUp className="mr-2 h-4 w-4" />
                              策略回测
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => handleDeleteClick(model)}
                              className="text-red-600 dark:text-red-400"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除模型
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <Dialog open={!!modelToDelete} onOpenChange={() => setModelToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除模型 <strong>{modelToDelete?.symbol}</strong> 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModelToDelete(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 训练配置弹窗 */}
      <Dialog open={showTrainingDialog} onOpenChange={setShowTrainingDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>训练新模型</DialogTitle>
            <DialogDescription>
              配置训练参数并开始训练机器学习模型
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <TrainingConfigPanel
              isInDialog={true}
              onTrainingStart={() => setShowTrainingMonitor(true)}
            />
          </div>
        </DialogContent>
      </Dialog>

      {/* 训练进度模态窗口 */}
      <Dialog open={showTrainingMonitor} onOpenChange={setShowTrainingMonitor}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>训练进度</DialogTitle>
            <DialogDescription>
              正在训练模型，请稍候...
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <TrainingMonitor />
          </div>
          {currentTask?.status === 'running' && (
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowTrainingMonitor(false)}>
                后台运行
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
