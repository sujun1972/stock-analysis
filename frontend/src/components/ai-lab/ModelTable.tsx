/**
 * 模型表格组件
 * 以表格形式展示所有训练完成的模型
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { useMLStore } from '@/store/mlStore';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { MoreHorizontal, PlayCircle, TrendingUp, Trash2, RefreshCw, Search, Info, Plus, Sparkles, User, ChevronLeft, ChevronRight, Rocket, X } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import TrainingConfigPanel from './TrainingConfigPanel';
import TrainingMonitor from './TrainingMonitor';
import ModelActionsMenu from './ModelActionsMenu';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

interface ModelTableProps {
  showTrainingDialog: boolean;
  setShowTrainingDialog: (show: boolean) => void;
}

export default function ModelTable({ showTrainingDialog, setShowTrainingDialog }: ModelTableProps) {
  const { models, setModels, setSelectedModel, currentTask, setCurrentTask } = useMLStore();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<any | null>(null);

  // 筛选和搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [modelTypeFilter, setModelTypeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [totalModels, setTotalModels] = useState(0);

  // 初始加载状态（用于判断是否显示引导页面）
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [hasAnyModels, setHasAnyModels] = useState(true);

  // 训练进度模态窗口状态
  const [showTrainingMonitor, setShowTrainingMonitor] = useState(false);

  // 批量选择状态
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [showBatchDeleteDialog, setShowBatchDeleteDialog] = useState(false);

  // 跟踪上一次处理的任务ID，避免重复显示成功提示
  // 使用 sessionStorage 持久化已处理的任务ID，避免页面导航时重复显示toast
  const getLastProcessedTaskId = () => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('lastProcessedTaskId');
    }
    return null;
  };

  const setLastProcessedTaskId = (taskId: string | null) => {
    if (typeof window !== 'undefined') {
      if (taskId) {
        sessionStorage.setItem('lastProcessedTaskId', taskId);
      } else {
        sessionStorage.removeItem('lastProcessedTaskId');
      }
    }
  };

  // 加载模型列表
  const loadModels = async (page: number = 1) => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pageSize
      };

      // 添加筛选条件（使用防抖后的搜索词）
      if (debouncedSearchQuery) {
        params.symbol = debouncedSearchQuery;
      }
      if (modelTypeFilter !== 'all') {
        params.model_type = modelTypeFilter;
      }
      if (sourceFilter !== 'all') {
        params.source = sourceFilter;
      }

      const response = await axios.get(`${API_BASE}/ml/models`, { params });
      setModels(response.data.models || []);
      setTotalPages(response.data.total_pages || 1);
      setTotalModels(response.data.total || 0);
      setCurrentPage(response.data.page || 1);

      // 判断是否有任何模型（在初始加载且无筛选条件时）
      if (isInitialLoad && !debouncedSearchQuery && modelTypeFilter === 'all' && sourceFilter === 'all') {
        setHasAnyModels(response.data.total > 0);
        setIsInitialLoad(false);
      }
    } catch (error) {
      console.error('加载模型列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadModels(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 搜索词防抖处理（200ms延迟）
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 筛选条件变化时重置到第一页（使用防抖后的搜索词）
  useEffect(() => {
    setCurrentPage(1);
    loadModels(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearchQuery, modelTypeFilter, sourceFilter]);


  // 批量选择辅助函数
  const toggleSelectAll = () => {
    if (selectedModels.size === models.length && models.length > 0) {
      setSelectedModels(new Set());
    } else {
      // 使用实验ID（唯一标识符）而不是model_id
      setSelectedModels(new Set(models.map(m => String(m.id))));
    }
  };

  const toggleSelectModel = (id: string) => {
    const newSelected = new Set(selectedModels);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedModels(newSelected);
  };

  // 批量删除
  const handleBatchDelete = async () => {
    try {
      // 将选中的实验ID转换为实验记录，以便删除
      const selectedIds = Array.from(selectedModels);
      const selectedExperiments = models.filter(m => selectedIds.includes(String(m.id)));

      // 批量删除所有选中的实验（使用实验ID）
      await Promise.all(
        selectedExperiments.map(exp =>
          axios.delete(`${API_BASE}/experiment/${exp.id}`)
        )
      );

      toast({
        title: '删除成功',
        description: `已删除 ${selectedModels.size} 个模型`,
      });

      // 清空选择并重新加载列表
      setSelectedModels(new Set());
      setShowBatchDeleteDialog(false);
      loadModels(currentPage);
    } catch (error: any) {
      console.error('批量删除失败:', error);
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: error.response?.data?.detail || error.message || '未知错误',
      });
    }
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
      loadModels(currentPage);
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
      const currentTaskId = currentTask.task_id;

      // 如果有训练任务在运行，显示训练监控窗口
      if (currentTask.status === 'running') {
        setShowTrainingMonitor(true);
      }
      // 如果训练完成，关闭监控窗口，刷新列表，显示成功提示
      else if (currentTask.status === 'completed') {
        setShowTrainingMonitor(false);
        setShowTrainingDialog(false);

        // 如果之前没有模型，现在有了
        setHasAnyModels(true);

        // 静默刷新模型列表
        loadModels(currentPage);

        // 只在任务ID变化时显示成功提示（避免页面导航时重复显示）
        const lastProcessedId = getLastProcessedTaskId();
        if (currentTaskId && lastProcessedId !== currentTaskId) {
          setLastProcessedTaskId(currentTaskId);
          toast({
            title: '训练完成',
            description: `模型 ${currentTask.config?.symbol} - ${currentTask.config?.model_type?.toUpperCase()} 训练成功！`,
          });

          // 显示 toast 后清除 currentTask，避免页面导航时重复触发
          setTimeout(() => {
            setCurrentTask(null);
          }, 100);
        }
      }
      // 如果训练失败，关闭监控窗口并清除任务
      else if (currentTask.status === 'failed') {
        setShowTrainingMonitor(false);
        // 失败后也清除任务
        setTimeout(() => {
          setCurrentTask(null);
        }, 100);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTask]);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CardTitle>模型仓库</CardTitle>
              {selectedModels.size > 0 && (
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-sm">
                    已选择 {selectedModels.size} 项
                  </Badge>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setShowBatchDeleteDialog(true)}
                    className="h-8"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    批量删除
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedModels(new Set())}
                    className="h-8"
                  >
                    <X className="h-4 w-4 mr-1" />
                    取消选择
                  </Button>
                </div>
              )}
            </div>
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

              {/* 来源筛选 */}
              <Select value={sourceFilter} onValueChange={setSourceFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="模型来源" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部来源</SelectItem>
                  <SelectItem value="auto_experiment">自动实验</SelectItem>
                  <SelectItem value="manual_training">手动训练</SelectItem>
                </SelectContent>
              </Select>

              {/* 刷新按钮 */}
              <Button variant="outline" size="icon" onClick={() => loadModels(currentPage)} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">
                    <Checkbox
                      checked={selectedModels.size === models.length && models.length > 0}
                      onCheckedChange={toggleSelectAll}
                      aria-label="全选"
                    />
                  </TableHead>
                  <TableHead>股票代码</TableHead>
                  <TableHead>模型类型</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead className="text-right">周期</TableHead>
                  <TableHead className="text-right">RMSE</TableHead>
                  <TableHead className="text-right">R²</TableHead>
                  <TableHead className="text-right">IC</TableHead>
                  <TableHead className="text-right">Rank IC</TableHead>
                  <TableHead className="text-right">评分</TableHead>
                  <TableHead className="text-right">年化收益</TableHead>
                  <TableHead className="text-right">夏普</TableHead>
                  <TableHead className="text-right">回撤</TableHead>
                  <TableHead className="text-right">胜率</TableHead>
                  <TableHead>训练时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  // 加载中状态
                  <TableRow>
                    <TableCell colSpan={17} className="text-center py-8">
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        <span className="ml-3 text-muted-foreground">加载模型列表...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : models.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={17} className="text-center py-12">
                      {!hasAnyModels ? (
                        // 完全没有模型时显示引导内容
                        <div className="space-y-6">
                          <div>
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                              开始训练您的第一个 AI 模型
                            </h2>
                            <p className="text-gray-500 dark:text-gray-400 mb-4">
                              您可以手动配置并训练单个模型，或使用自动化实验批量训练
                            </p>
                            <div className="flex gap-3 justify-center">
                              <Button
                                variant="outline"
                                onClick={() => router.push('/auto-experiment')}
                                className="flex items-center gap-2"
                              >
                                <Rocket className="h-4 w-4" />
                                自动化实验（推荐）
                              </Button>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-base">数据驱动</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  自动获取60+技术指标和Alpha因子
                                </p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-base">智能预测</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  LightGBM和GRU深度学习模型
                                </p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-base">深度观察</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  特征重要性、快照查看器
                                </p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-base">一键回测</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  直接使用模型进行策略回测
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                      ) : (
                        // 有模型但筛选结果为空时显示提示
                        <div className="text-muted-foreground">
                          未找到匹配的模型
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  models.map((model) => (
                    <TableRow key={model.id || model.model_id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedModels.has(String(model.id))}
                          onCheckedChange={() => toggleSelectModel(String(model.id))}
                          aria-label={`选择模型 ${model.symbol}`}
                        />
                      </TableCell>
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
                      <TableCell>
                        {model.source === 'auto_experiment' ? (
                          <Badge variant="secondary" className="text-xs flex items-center gap-1 w-fit">
                            <Sparkles className="h-3 w-3" />
                            自动实验
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs flex items-center gap-1 w-fit">
                            <User className="h-3 w-3" />
                            手动训练
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right text-sm">{model.target_period}天</TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.metrics?.rmse?.toFixed(4) || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.metrics?.r2?.toFixed(4) || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-blue-600 dark:text-blue-400">
                        {model.metrics?.ic?.toFixed(4) || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-blue-600 dark:text-blue-400">
                        {model.metrics?.rank_ic?.toFixed(4) || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-purple-600 dark:text-purple-400">
                        {model.rank_score?.toFixed(2) || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.annual_return !== null && model.annual_return !== undefined ? (
                          <span className={model.annual_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                            {model.annual_return.toFixed(2)}%
                          </span>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.sharpe_ratio !== null && model.sharpe_ratio !== undefined ? model.sharpe_ratio.toFixed(2) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-red-600 dark:text-red-400">
                        {model.max_drawdown !== null && model.max_drawdown !== undefined ? `${model.max_drawdown.toFixed(2)}%` : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {model.win_rate !== null && model.win_rate !== undefined ? `${(model.win_rate * 100).toFixed(2)}%` : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {model.trained_at ? new Date(model.trained_at).toLocaleString('zh-CN', {
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        }) : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <ModelActionsMenu
                          model={{
                            id: model.id,
                            experiment_id: model.id,
                            model_id: model.model_id,
                            symbol: model.symbol,
                            config: model.config
                          }}
                          onDelete={handleDeleteClick}
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页控件 */}
          {totalModels > 0 && (
            <div className="flex items-center justify-between px-2 py-4">
              <div className="text-sm text-muted-foreground">
                共 {totalModels} 个模型，第 {currentPage} / {totalPages} 页
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadModels(currentPage - 1)}
                  disabled={currentPage <= 1 || loading}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadModels(currentPage + 1)}
                  disabled={currentPage >= totalPages || loading}
                >
                  下一页
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
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

      {/* 批量删除确认对话框 */}
      <Dialog open={showBatchDeleteDialog} onOpenChange={setShowBatchDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
            <DialogDescription>
              确定要删除选中的 <strong>{selectedModels.size}</strong> 个模型吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBatchDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleBatchDelete}>
              删除 {selectedModels.size} 个模型
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
