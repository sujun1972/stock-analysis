/**
 * 模型表格组件
 * 以表格形式展示所有训练完成的模型
 */

'use client';

import { useEffect, useState, useCallback, memo } from 'react';
import { useMLStore } from '@/stores/ml-store';
import { useRouter } from 'next/navigation';
import axiosInstance from '@/lib/api/axios-instance'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Trash2, Plus, Sparkles, User, X, Rocket, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { extractApiError } from '@/lib/error-formatter';
import { useModels, useDeleteModel } from '@/hooks/useModels';
import TrainingConfigPanel from './TrainingConfigPanel';
import TrainingMonitor from './TrainingMonitor';
import ModelActionsMenu from './ModelActionsMenu';
import ModelTableFilters from './ModelTableFilters';
import ModelTableHeader from './ModelTableHeader';
import BatchDeleteDialog from './BatchDeleteDialog';
import EmptyState from './EmptyState';
import Pagination from './Pagination';
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


interface ModelTableProps {
  showTrainingDialog: boolean;
  setShowTrainingDialog: (show: boolean) => void;
}

// Memoized 表格行组件，避免不必要的重渲染
const ModelRow = memo(function ModelRow({
  model,
  isSelected,
  onToggleSelect,
  onDelete
}: {
  model: any;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onDelete: (model: any) => void;
}) {
  return (
    <TableRow>
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={() => onToggleSelect(String(model.id))}
          aria-label={`选择模型 ${model.symbol}`}
        />
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-1.5">
          <div className="font-medium">{model.symbol}</div>
          <div className="flex items-center gap-1.5">
            <span
              className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded ${
                model.model_type === 'lightgbm'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
              }`}
            >
              {model.model_type.toUpperCase()}
            </span>
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
          </div>
        </div>
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
        {model.rank_score !== null && model.rank_score !== undefined ? model.rank_score.toFixed(2) : '-'}
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
          onDelete={onDelete}
        />
      </TableCell>
    </TableRow>
  );
});

ModelRow.displayName = 'ModelRow';

export default function ModelTable({ showTrainingDialog, setShowTrainingDialog }: ModelTableProps) {
  const { setModels, setSelectedModel, currentTask, setCurrentTask } = useMLStore();
  const router = useRouter();
  const { toast } = useToast();
  const [modelToDelete, setModelToDelete] = useState<any | null>(null);

  // 筛选和搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [modelTypeFilter, setModelTypeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);

  // 排序状态
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // 初始加载状态（用于判断是否显示引导页面）
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [hasAnyModels, setHasAnyModels] = useState(true);

  // 使用 React Query hooks
  const { data: modelsData, isLoading, refetch } = useModels({
    skip: (currentPage - 1) * pageSize,
    limit: pageSize,
    model_type: modelTypeFilter !== 'all' ? modelTypeFilter : undefined,
    source: sourceFilter !== 'all' ? sourceFilter : undefined,
    search: debouncedSearchQuery || undefined,
    sort_by: sortBy || undefined,
    sort_order: sortOrder,
  });

  const deleteModelMutation = useDeleteModel();

  const models = modelsData?.models || [];
  const totalPages = modelsData?.total_pages || 1;
  const totalModels = modelsData?.total || 0;

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

  // 更新 Zustand store 和初始加载状态
  useEffect(() => {
    if (modelsData) {
      setModels(modelsData.models || []);

      // 判断是否有任何模型（在初始加载且无筛选条件时）
      if (isInitialLoad && !debouncedSearchQuery && modelTypeFilter === 'all' && sourceFilter === 'all') {
        setHasAnyModels(modelsData.total > 0);
        setIsInitialLoad(false);
      }
    }
  }, [modelsData, isInitialLoad, debouncedSearchQuery, modelTypeFilter, sourceFilter, setModels]);

  // 搜索词防抖处理（200ms延迟）
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 筛选条件或排序变化时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearchQuery, modelTypeFilter, sourceFilter, sortBy, sortOrder]);


  // 排序处理函数 - 使用 useCallback 优化
  const handleSort = useCallback((field: string) => {
    if (sortBy === field) {
      // 同一字段，切换排序顺序
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // 新字段，默认降序
      setSortBy(field);
      setSortOrder('desc');
    }
  }, [sortBy, sortOrder]);

  // 获取排序图标
  const getSortIcon = useCallback((field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="h-4 w-4 ml-1 text-gray-400" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="h-4 w-4 ml-1 text-blue-600" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1 text-blue-600" />
    );
  }, [sortBy, sortOrder]);

  // 批量选择辅助函数 - 使用 useCallback 优化
  const toggleSelectAll = useCallback(() => {
    if (selectedModels.size === models.length && models.length > 0) {
      setSelectedModels(new Set());
    } else {
      // 使用实验ID（唯一标识符）而不是model_id
      setSelectedModels(new Set(models.map((m: any) => String(m.id))));
    }
  }, [selectedModels.size, models]);

  const toggleSelectModel = useCallback((id: string) => {
    const newSelected = new Set(selectedModels);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedModels(newSelected);
  }, [selectedModels]);

  // 批量删除
  const handleBatchDelete = async () => {
    try {
      // 将选中的实验ID转换为实验记录，以便删除
      const selectedIds = Array.from(selectedModels);
      const selectedExperiments = models.filter((m: any) => selectedIds.includes(String(m.id)));

      // 批量删除所有选中的实验（使用实验ID）
      await Promise.all(
        selectedExperiments.map((exp: any) =>
          axiosInstance.delete(`/api/experiment/${exp.id}`)
        )
      );

      toast({
        title: '删除成功',
        description: `已删除 ${selectedModels.size} 个模型`,
      });

      // 清空选择并重新加载列表
      setSelectedModels(new Set());
      setShowBatchDeleteDialog(false);
      refetch();
    } catch (error: any) {
      console.error('批量删除失败:', error);
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: extractApiError(error, '未知错误'),
      });
    }
  };


  // 删除模型 - 使用 useCallback 优化
  const handleDeleteClick = useCallback((model: any) => {
    setModelToDelete(model);
  }, []);

  const confirmDelete = async () => {
    if (!modelToDelete) return;

    try {
      await deleteModelMutation.mutateAsync(modelToDelete.id);

      toast({
        title: '删除成功',
        description: `模型 ${modelToDelete.symbol} 已删除`,
      });

      setModelToDelete(null);
    } catch (error: any) {
      console.error('删除模型失败:', error);
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: extractApiError(error, '未知错误'),
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
        refetch();

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
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3 min-w-0">
              <CardTitle>模型仓库</CardTitle>
              {selectedModels.size > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary" className="text-sm tabular-nums">
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
            <ModelTableFilters
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              modelTypeFilter={modelTypeFilter}
              onModelTypeChange={setModelTypeFilter}
              sourceFilter={sourceFilter}
              onSourceChange={setSourceFilter}
              isLoading={isLoading}
              onRefresh={() => refetch()}
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto scrollbar-thin">
            <Table className="min-w-[1200px]">
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
                  <TableHead className="text-right">周期</TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('rmse')}
                  >
                    <div className="flex items-center justify-end">
                      RMSE
                      {getSortIcon('rmse')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('r2')}
                  >
                    <div className="flex items-center justify-end">
                      R²
                      {getSortIcon('r2')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('ic')}
                  >
                    <div className="flex items-center justify-end">
                      IC
                      {getSortIcon('ic')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('rank_ic')}
                  >
                    <div className="flex items-center justify-end">
                      Rank IC
                      {getSortIcon('rank_ic')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('rank_score')}
                  >
                    <div className="flex items-center justify-end">
                      评分
                      {getSortIcon('rank_score')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('annual_return')}
                  >
                    <div className="flex items-center justify-end">
                      年化收益
                      {getSortIcon('annual_return')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('sharpe_ratio')}
                  >
                    <div className="flex items-center justify-end">
                      夏普
                      {getSortIcon('sharpe_ratio')}
                    </div>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none"
                    onClick={() => handleSort('max_drawdown')}
                  >
                    <div className="flex items-center justify-end">
                      回撤
                      {getSortIcon('max_drawdown')}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">胜率</TableHead>
                  <TableHead>训练时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  // 加载中状态
                  <TableRow>
                    <TableCell colSpan={15} className="text-center py-8">
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                        <span className="ml-3 text-muted-foreground">加载模型列表...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : models.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={15} className="text-center py-12">
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
                  models.map((model: any) => (
                    <ModelRow
                      key={model.id || model.model_id}
                      model={model}
                      isSelected={selectedModels.has(String(model.id))}
                      onToggleSelect={toggleSelectModel}
                      onDelete={handleDeleteClick}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页控件 */}
          {totalModels > 0 && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-2 py-4">
              <div className="text-sm text-muted-foreground tabular-nums">
                共 {totalModels} 个模型，第 {currentPage} / {totalPages} 页
              </div>
              <div className="flex items-center gap-2 justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => prev - 1)}
                  disabled={currentPage <= 1 || isLoading}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => prev + 1)}
                  disabled={currentPage >= totalPages || isLoading}
                >
                  下一页
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 指标说明卡片 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">评估指标说明</CardTitle>
          <CardDescription>了解各项模型评估指标的含义，帮助您更好地选择和使用模型</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* 训练指标 */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
                <span className="text-lg">📊</span>
                训练指标
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-blue-800 dark:text-blue-200">RMSE</span>
                  <span className="text-blue-700 dark:text-blue-300"> (均方根误差)</span>
                  <p className="text-blue-600 dark:text-blue-400 mt-1">预测值与真实值的平均偏差，越小越好。衡量模型的基本预测准确性。</p>
                </div>
                <div className="pt-2 border-t border-blue-200 dark:border-blue-700">
                  <span className="font-medium text-blue-800 dark:text-blue-200">R²</span>
                  <span className="text-blue-700 dark:text-blue-300"> (决定系数)</span>
                  <p className="text-blue-600 dark:text-blue-400 mt-1">模型对数据的拟合程度，范围 0-1，越接近 1 表示拟合越好。</p>
                </div>
              </div>
            </div>

            {/* 信息系数指标 */}
            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
              <h4 className="font-semibold text-purple-900 dark:text-purple-100 mb-2 flex items-center gap-2">
                <span className="text-lg">🎯</span>
                信息系数 (IC)
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-purple-800 dark:text-purple-200">IC</span>
                  <span className="text-purple-700 dark:text-purple-300"> (信息系数)</span>
                  <p className="text-purple-600 dark:text-purple-400 mt-1">预测值与实际收益的相关性，范围 -1 到 1。绝对值越大预测能力越强，通常 &gt;0.03 即可用。</p>
                </div>
                <div className="pt-2 border-t border-purple-200 dark:border-purple-700">
                  <span className="font-medium text-purple-800 dark:text-purple-200">Rank IC</span>
                  <span className="text-purple-700 dark:text-purple-300"> (排序相关性)</span>
                  <p className="text-purple-600 dark:text-purple-400 mt-1">预测排序与实际排序的相关性，对异常值更稳健，是选股策略的核心指标。</p>
                </div>
              </div>
            </div>

            {/* 综合评分 */}
            <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
              <h4 className="font-semibold text-indigo-900 dark:text-indigo-100 mb-2 flex items-center gap-2">
                <span className="text-lg">⭐</span>
                综合评分
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-indigo-800 dark:text-indigo-200">评分</span>
                  <span className="text-indigo-700 dark:text-indigo-300"> (Rank Score)</span>
                  <p className="text-indigo-600 dark:text-indigo-400 mt-1">综合训练指标和回测指标的加权评分。分数越高表示模型整体表现越好。正分表示模型总体可用，负分表示需要优化。</p>
                </div>
              </div>
            </div>

            {/* 收益指标 */}
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <h4 className="font-semibold text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
                <span className="text-lg">💰</span>
                收益指标
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-green-800 dark:text-green-200">年化收益</span>
                  <span className="text-green-700 dark:text-green-300"> (Annual Return)</span>
                  <p className="text-green-600 dark:text-green-400 mt-1">策略的年化收益率，正值表示盈利，负值表示亏损。通常期望 &gt;15%。</p>
                </div>
                <div className="pt-2 border-t border-green-200 dark:border-green-700">
                  <span className="font-medium text-green-800 dark:text-green-200">胜率</span>
                  <span className="text-green-700 dark:text-green-300"> (Win Rate)</span>
                  <p className="text-green-600 dark:text-green-400 mt-1">盈利交易占总交易的比例。高胜率 (&gt;50%) 意味着策略稳定性好。</p>
                </div>
              </div>
            </div>

            {/* 风险指标 */}
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <h4 className="font-semibold text-red-900 dark:text-red-100 mb-2 flex items-center gap-2">
                <span className="text-lg">⚠️</span>
                风险指标
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-red-800 dark:text-red-200">最大回撤</span>
                  <span className="text-red-700 dark:text-red-300"> (Max Drawdown)</span>
                  <p className="text-red-600 dark:text-red-400 mt-1">账户从最高点到最低点的最大跌幅，越小越好。表示策略可能面临的最大亏损，通常期望 &lt;20%。</p>
                </div>
              </div>
            </div>

            {/* 风险调整收益 */}
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-2 flex items-center gap-2">
                <span className="text-lg">📈</span>
                风险调整收益
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-amber-800 dark:text-amber-200">夏普比率</span>
                  <span className="text-amber-700 dark:text-amber-300"> (Sharpe Ratio)</span>
                  <p className="text-amber-600 dark:text-amber-400 mt-1">每承担一单位风险获得的超额收益。&gt;1 良好，&gt;2 优秀，&gt;3 卓越。是评估策略性价比的关键指标。</p>
                </div>
              </div>
            </div>
          </div>

          {/* 使用建议 */}
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
              <span className="text-lg">💡</span>
              选择建议
            </h4>
            <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
              <p><strong>优先考虑：</strong>综合评分为正且较高、夏普比率 &gt;1.5、最大回撤 &lt;15% 的模型</p>
              <p><strong>IC 指标：</strong>Rank IC &gt; 0.05 说明模型有较强的选股能力</p>
              <p><strong>稳健性：</strong>胜率 &gt;50% 且回撤小的模型更适合长期使用</p>
              <p><strong>激进型：</strong>可选择年化收益高但回撤稍大的模型，注意仓位管理</p>
              <p><strong>负评分模型：</strong>评分为负表示模型整体表现较差，建议调整参数或重新训练</p>
            </div>
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
