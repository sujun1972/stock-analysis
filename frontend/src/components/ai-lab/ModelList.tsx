/**
 * 模型列表管理组件
 * 显示所有训练完成的模型，支持选择、查看详情、删除等操作
 */

'use client';

import { useEffect, useState } from 'react';
import { useMLStore } from '@/store/mlStore';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { PlayCircle, Settings, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

interface ModelCardProps {
  model: any;
  isSelected: boolean;
  onSelect: () => void;
  onPredict: () => void;
  onDelete: () => void;
  onQuickBacktest: () => void;
  onAdvancedBacktest: () => void;
}

function ModelCard({ model, isSelected, onSelect, onPredict, onDelete, onQuickBacktest, onAdvancedBacktest }: ModelCardProps) {
  const { model_id, symbol, model_type, target_period, metrics, trained_at } = model;

  return (
    <div
      className={`
        relative p-4 rounded-lg border-2 transition-all cursor-pointer
        ${isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
        }
      `}
      onClick={onSelect}
    >
      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute top-2 right-2">
          <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded-full">
            ✓ 已选中
          </span>
        </div>
      )}

      {/* 模型基本信息 */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {symbol}
          </h3>
          <span className={`
            px-2 py-0.5 text-xs font-medium rounded
            ${model_type === 'lightgbm' ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'}
          `}>
            {model_type.toUpperCase()}
          </span>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          目标周期: {target_period}天 | 训练时间: {trained_at?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$1-$2-$3')}
        </div>
      </div>

      {/* 性能指标 */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">RMSE</div>
          <div className="text-sm font-semibold text-gray-900 dark:text-white">
            {metrics?.rmse?.toFixed(4) || 'N/A'}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">R²</div>
          <div className="text-sm font-semibold text-gray-900 dark:text-white">
            {metrics?.r2?.toFixed(4) || 'N/A'}
          </div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/30 rounded p-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">IC</div>
          <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
            {metrics?.ic?.toFixed(4) || 'N/A'}
          </div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/30 rounded p-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">Rank IC</div>
          <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
            {metrics?.rank_ic?.toFixed(4) || 'N/A'}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="space-y-2">
        {/* 第一行：预测和删除 */}
        <div className="flex gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onPredict();
            }}
            className="flex-1 h-8"
          >
            <PlayCircle className="h-3.5 w-3.5 mr-1" />
            运行预测
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="h-8 text-destructive border-destructive hover:bg-destructive hover:text-destructive-foreground"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* 第二行：回测按钮（仅选中时显示） */}
        {isSelected && (
          <div className="flex gap-2 pt-2 border-t border-blue-200 dark:border-blue-800">
            <Button
              variant="default"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onQuickBacktest();
              }}
              className="flex-1 h-8 bg-green-600 hover:bg-green-700"
            >
              一键回测
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onAdvancedBacktest();
              }}
              className="flex-1 h-8"
            >
              <Settings className="h-3.5 w-3.5 mr-1" />
              高级回测
            </Button>
          </div>
        )}
      </div>

      {/* 模型ID（调试用） */}
      <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-400 truncate" title={model_id}>
          ID: {model_id.substring(0, 16)}...
        </div>
      </div>
    </div>
  );
}

export default function ModelList() {
  const { models, setModels, selectedModel, setSelectedModel, setPredictions, currentTask } = useMLStore();
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterModelType, setFilterModelType] = useState('');
  const [backtestingModelId, setBacktestingModelId] = useState<string | null>(null);
  const [modelToDelete, setModelToDelete] = useState<any | null>(null);

  // 加载模型列表
  const loadModels = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (filterSymbol) params.symbol = filterSymbol;
      if (filterModelType) params.model_type = filterModelType;

      const response = await axios.get(`${API_BASE}/ml/models`, { params });
      setModels(response.data.models || []);
    } catch (error) {
      console.error('加载模型列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载和过滤条件变化时加载
  useEffect(() => {
    loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSymbol, filterModelType]);

  // 监听训练任务状态，训练完成后自动刷新模型列表
  useEffect(() => {
    if (currentTask?.status === 'completed') {
      // 延迟一小段时间确保后端已保存模型
      const timer = setTimeout(() => {
        loadModels();
      }, 500);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTask?.status]);

  // 选中模型
  const handleSelectModel = (model: any) => {
    setSelectedModel(model);
  };

  // 运行预测 - 直接跳转到预测分析页面，在那里执行预测
  const handlePredict = (model: any) => {
    // 设置选中的模型
    setSelectedModel(model);

    // 直接跳转到预测分析页面，并传递modelId参数
    // 预测页面会自动运行预测
    router.push(`/ai-lab/prediction?modelId=${model.model_id}`);
  };

  // 打开删除确认对话框
  const handleDeleteClick = (model: any) => {
    setModelToDelete(model);
  };

  // 确认删除模型
  const confirmDelete = async () => {
    if (!modelToDelete) return;

    try {
      await axios.delete(`${API_BASE}/ml/tasks/${modelToDelete.model_id}`);

      // 如果删除的是当前选中的模型，清空选中状态
      if (selectedModel?.model_id === modelToDelete.model_id) {
        setSelectedModel(null);
        setPredictions([]);
      }

      // 重新加载列表
      loadModels();

      // 显示成功提示
      toast({
        variant: 'success',
        title: '删除成功',
        description: `模型 ${modelToDelete.symbol} (${modelToDelete.model_type.toUpperCase()}) 已删除`,
      });
    } catch (error: any) {
      console.error('删除失败:', error);

      // 显示错误提示
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: error.response?.data?.detail || error.message || '未知错误',
      });
    } finally {
      setModelToDelete(null);
    }
  };

  // 一键回测
  const handleQuickBacktest = async (model: any) => {
    setBacktestingModelId(model.model_id);
    try {
      const config = model.config;

      // 创建回测任务
      const response = await axios.post(`${API_BASE}/backtest/run`, {
        symbols: model.symbol,
        start_date: config.start_date,
        end_date: config.end_date,
        initial_cash: 100000,

        // 使用ML模型信号作为策略
        strategy_id: 'ml_model',
        strategy_params: {
          model_id: model.model_id,
          // 注意: model_type 和 target_period 已移除，这些信息在模型元数据中

          // 交易阈值
          buy_threshold: 1.0,
          sell_threshold: -1.0,

          // 交易设置
          commission: 0.0003,
          slippage: 0.001,

          // 风控参数
          position_size: 1.0,
          stop_loss: 0.05,
          take_profit: 0.10,
        },
      });

      // 检查响应是否成功
      if (response.data.status === 'success' && response.data.data) {
        const backtestId = response.data.data.task_id;
        // 跳转到回测页面，带上 strategy_id 参数
        router.push(`/backtest?task_id=${backtestId}&strategy_id=ml_model`);
      } else {
        throw new Error('回测任务创建失败：响应格式错误');
      }
    } catch (error: any) {
      console.error('创建回测任务失败:', error);
      let errorMessage = '未知错误';
      if (error.response?.data) {
        const errorData = error.response.data;
        errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
      } else if (error.message) {
        errorMessage = error.message;
      }

      // 显示错误提示
      toast({
        variant: 'destructive',
        title: '创建回测任务失败',
        description: errorMessage,
      });
    } finally {
      setBacktestingModelId(null);
    }
  };

  // 高级回测（跳转到回测页面并预填参数）
  const handleAdvancedBacktest = (model: any) => {
    // 跳转到回测页面,使用ml类型
    // id为model_id
    router.push(`/backtest?type=ml&id=${model.model_id}`);
  };

  return (
    <Card>
      <CardHeader>
        {/* 标题行 - 标题和刷新按钮左右排列 */}
        <div className="flex items-center justify-between">
          <CardTitle>模型仓库</CardTitle>
          <Button
            onClick={loadModels}
            variant="outline"
            size="sm"
          >
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 过滤器 */}
        <div className="flex gap-3">
          <Input
            type="text"
            placeholder="股票代码过滤..."
            value={filterSymbol}
            onChange={(e) => setFilterSymbol(e.target.value)}
            className="flex-1"
          />
          <Select value={filterModelType || "all"} onValueChange={(value) => setFilterModelType(value === "all" ? "" : value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="所有模型类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">所有模型类型</SelectItem>
              <SelectItem value="lightgbm">LightGBM</SelectItem>
              <SelectItem value="gru">GRU</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 模型列表 */}
        {loading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            加载中...
          </div>
        ) : models.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无训练完成的模型，请先创建训练任务
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {models.map((model) => (
              <ModelCard
                key={model.model_id}
                model={model}
                isSelected={selectedModel?.model_id === model.model_id}
                onSelect={() => handleSelectModel(model)}
                onPredict={() => handlePredict(model)}
                onDelete={() => handleDeleteClick(model)}
                onQuickBacktest={() => handleQuickBacktest(model)}
                onAdvancedBacktest={() => handleAdvancedBacktest(model)}
              />
            ))}
          </div>
        )}

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

        {/* 删除确认对话框 */}
        <Dialog open={!!modelToDelete} onOpenChange={(open) => !open && setModelToDelete(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>确认删除模型</DialogTitle>
              <DialogDescription>
                确定要删除模型 <span className="font-semibold text-gray-900 dark:text-white">{modelToDelete?.symbol}</span> ({modelToDelete?.model_type?.toUpperCase()}) 吗？
                <br />
                此操作无法撤销，模型文件将被永久删除。
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setModelToDelete(null)}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
              >
                确认删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
