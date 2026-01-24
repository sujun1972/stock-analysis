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
import { MoreHorizontal, PlayCircle, TrendingUp, Settings, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
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
  const { models, setModels, setSelectedModel } = useMLStore();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [backtestingModelId, setBacktestingModelId] = useState<string | null>(null);
  const [modelToDelete, setModelToDelete] = useState<any | null>(null);

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

  // 一键回测
  const handleQuickBacktest = async (model: any) => {
    setBacktestingModelId(model.model_id);
    try {
      const response = await axios.post(`${API_BASE}/backtest/run`, {
        strategy_id: 'ml_model',
        strategy_params: {
          model_id: model.model_id,
          buy_threshold: 1.0,
          sell_threshold: -1.0,
          commission: 0.0003,
          slippage: 0.001,
          position_size: 1.0,
          stop_loss: 0.05,
          take_profit: 0.10,
        },
        symbol: model.symbol,
        start_date: model.config?.start_date || '2020-01-01',
        end_date: model.config?.end_date || new Date().toISOString().split('T')[0],
        initial_capital: 100000,
      });

      toast({
        title: '回测任务已创建',
        description: `正在为模型 ${model.symbol} 运行回测...`,
      });

      router.push(`/backtest?task_id=${response.data.task_id}`);
    } catch (error: any) {
      console.error('创建回测任务失败:', error);
      toast({
        variant: 'destructive',
        title: '回测失败',
        description: error.response?.data?.detail || error.message || '未知错误',
      });
    } finally {
      setBacktestingModelId(null);
    }
  };

  // 高级回测
  const handleAdvancedBacktest = (model: any) => {
    setSelectedModel(model);
    router.push(`/backtest?strategy_id=ml_model&model_id=${model.model_id}&symbol=${model.symbol}`);
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
          <CardTitle>模型仓库</CardTitle>
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
                {models.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                      暂无模型数据
                    </TableCell>
                  </TableRow>
                ) : (
                  models.map((model) => (
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
                            <DropdownMenuItem onClick={() => handlePredict(model)}>
                              <PlayCircle className="mr-2 h-4 w-4" />
                              运行预测
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleQuickBacktest(model)}
                              disabled={backtestingModelId === model.model_id}
                            >
                              <TrendingUp className="mr-2 h-4 w-4" />
                              一键回测
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleAdvancedBacktest(model)}>
                              <Settings className="mr-2 h-4 w-4" />
                              高级回测
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

      {/* 加载提示 - 回测 */}
      {backtestingModelId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
              <div className="text-gray-900 dark:text-white font-medium">
                正在创建回测任务，请稍候...
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
