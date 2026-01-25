/**
 * 模型详情页面
 *
 * 功能：
 * - 展示模型的基本信息（股票代码、模型类型、预测周期、训练时间等）
 * - 完整展示所有训练指标（RMSE、R²、IC、Rank IC、样本数等）
 * - 展示回测指标（综合评分、年化收益、夏普比率、最大回撤、胜率）
 * - 展示训练配置详情
 * - 特征重要性可视化（LightGBM）或训练历史曲线（GRU）
 * - 支持运行预测、策略回测、数据导出功能
 */

'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMLStore } from '@/store/mlStore';
import FeatureImportance from '@/components/ai-lab/FeatureImportance';
import TrainingHistory from '@/components/ai-lab/TrainingHistory';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PlayCircle, TrendingUp, Loader2, Download } from 'lucide-react';
import axios from 'axios';
import { useToast } from '@/hooks/use-toast';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

function ModelDetailsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { models, setModels, setSelectedModel, setCurrentTask } = useMLStore();
  const { toast } = useToast();

  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [taskDetail, setTaskDetail] = useState<any>(null);
  const [error, setError] = useState<string>('');

  // 加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await axios.get(`${API_BASE}/ml/models`, {
          params: { limit: 100 }
        });
        setModels(response.data.models || []);
      } catch (err) {
        console.error('加载模型列表失败:', err);
      }
    };

    if (models.length === 0) {
      loadModels();
    }
  }, [models.length, setModels]);

  // 初始化：从URL参数获取experimentId
  useEffect(() => {
    const experimentIdFromUrl = searchParams.get('experimentId');
    const modelIdFromUrl = searchParams.get('modelId'); // 兼容旧URL

    if (experimentIdFromUrl) {
      setSelectedModelId(experimentIdFromUrl);
      loadModelDetails(experimentIdFromUrl);
    } else if (modelIdFromUrl && models.length > 0) {
      // 兼容旧的modelId参数，通过models找到对应的experimentId
      const model = models.find(m => m.model_id === modelIdFromUrl);
      if (model && model.id) {
        setSelectedModelId(String(model.id));
        loadModelDetails(String(model.id));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, models]);

  // 加载模型详细信息（使用实验ID）
  const loadModelDetails = async (experimentId: string) => {
    if (!experimentId) return;

    setLoading(true);
    setError('');

    try {
      const response = await axios.get(`${API_BASE}/experiment/${experimentId}`);
      const experiment = response.data.data;

      // 转换为旧的task格式以兼容现有组件
      const task = {
        task_id: String(experiment.id),
        model_id: experiment.model_id,
        model_name: experiment.model_id,
        status: experiment.status,
        config: experiment.config,
        metrics: experiment.train_metrics,
        feature_importance: experiment.feature_importance,
        model_path: experiment.model_path,
        started_at: experiment.train_started_at,
        completed_at: experiment.train_completed_at,
        created_at: experiment.created_at,
        progress: 100, // 已完成的模型进度为100%
        current_step: experiment.status === 'completed' ? '训练完成' : experiment.status,
        error_message: experiment.error_message,
      };

      setTaskDetail(task);

      // 更新store中的currentTask以支持FeatureImportance和TrainingHistory组件
      setCurrentTask(task);

      // 更新selectedModel
      const model = models.find(m => String(m.id) === experimentId);
      if (model) {
        setSelectedModel(model);
      }
    } catch (err: any) {
      console.error('加载模型详情失败:', err);
      setError(err.response?.data?.detail || err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理模型选择变化
  const handleModelChange = (experimentId: string) => {
    setSelectedModelId(experimentId);
    router.push(`/ai-lab/model-details?experimentId=${experimentId}`);
    loadModelDetails(experimentId);
  };

  // 运行预测
  const handlePredict = () => {
    if (selectedModelId) {
      // 使用 experimentId 而不是 modelId
      router.push(`/ai-lab/prediction?experimentId=${selectedModelId}`);
    }
  };

  // 跳转到回测页面（预填参数并自动运行）
  const handleQuickBacktest = () => {
    if (!taskDetail) return;

    // 使用 experiment ID 查找模型
    const model = models.find(m => String(m.id) === selectedModelId);
    if (!model) return;

    // 构建回测配置
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

    // 跳转到回测页面，通过 URL 参数传递配置
    const configParam = encodeURIComponent(JSON.stringify(config));
    router.push(`/backtest?config=${configParam}`);
  };

  /**
   * 导出模型完整数据到剪贴板
   *
   * 导出内容包括：
   * - 基本信息（ID、状态、路径、时间等）
   * - 训练配置（数据范围、模型参数、特征选择等）
   * - 训练指标（RMSE、R²、IC、Rank IC、样本数等）
   * - 回测指标（评分、年化收益、夏普、回撤、胜率等）
   * - 特征重要性和训练历史
   */
  const handleExportData = async () => {
    if (!taskDetail) {
      toast({
        variant: 'destructive',
        title: '导出失败',
        description: '没有可用的模型数据',
      });
      return;
    }

    try {
      // 获取当前选中模型的完整数据（包含回测指标）
      const selectedModelData = models.find(m => String(m.id) === selectedModelId);

      // 收集所有模型数据
      const exportData = {
        // 基本信息
        model_info: {
          experiment_id: taskDetail.task_id,
          model_id: taskDetail.model_id,
          model_name: taskDetail.model_name,
          status: taskDetail.status,
          model_path: taskDetail.model_path,
          created_at: taskDetail.created_at,
          started_at: taskDetail.started_at,
          completed_at: taskDetail.completed_at,
          symbol: taskDetail.config?.symbol,
          model_type: taskDetail.config?.model_type,
          target_period: taskDetail.config?.target_period,
          source: selectedModelData?.source,
        },

        // 训练配置（完整配置，包含默认值）
        training_config: {
          // 基本配置
          symbol: taskDetail.config?.symbol,
          start_date: taskDetail.config?.start_date,
          end_date: taskDetail.config?.end_date,
          model_type: taskDetail.config?.model_type,
          target_period: taskDetail.config?.target_period ?? 5,

          // 数据集划分（如果后端没保存，使用默认值）
          train_ratio: taskDetail.config?.train_ratio ?? 0.7,
          valid_ratio: taskDetail.config?.valid_ratio ?? 0.15,
          test_ratio: taskDetail.config?.test_ratio ?? (1 - (taskDetail.config?.train_ratio ?? 0.7) - (taskDetail.config?.valid_ratio ?? 0.15)),

          // 特征选择（默认值）
          use_technical_indicators: taskDetail.config?.use_technical_indicators ?? true,
          use_alpha_factors: taskDetail.config?.use_alpha_factors ?? true,
          selected_features: taskDetail.config?.selected_features ?? null,

          // 数据处理（默认值）
          scaler_type: taskDetail.config?.scaler_type ?? 'robust',
          scale_features: taskDetail.config?.scale_features ?? true,
          balance_samples: taskDetail.config?.balance_samples ?? false,
          balance_method: taskDetail.config?.balance_method ?? 'undersample',

          // 模型参数
          model_params: taskDetail.config?.model_params ?? null,

          // GRU 特定参数（默认值）
          ...(taskDetail.config?.model_type === 'gru' && {
            seq_length: taskDetail.config?.seq_length ?? 20,
            batch_size: taskDetail.config?.batch_size ?? 64,
            epochs: taskDetail.config?.epochs ?? 100,
          }),

          // LightGBM 特定参数（默认值）
          ...(taskDetail.config?.model_type === 'lightgbm' && {
            early_stopping_rounds: taskDetail.config?.early_stopping_rounds ?? 50,
          }),
        },

        // 训练指标（包含所有 metrics 字段）
        training_metrics: taskDetail.metrics || {},

        // 回测指标（如果有）
        backtest_metrics: selectedModelData?.backtest_metrics || null,

        // 特征重要性
        feature_importance: taskDetail.feature_importance,

        // 训练历史（GRU模型）
        training_history: taskDetail.training_history,

        // 其他信息
        current_step: taskDetail.current_step,
        progress: taskDetail.progress,
        error_message: taskDetail.error_message,
      };

      // 转换为格式化的 JSON 字符串
      const jsonString = JSON.stringify(exportData, null, 2);

      // 复制到剪贴板
      await navigator.clipboard.writeText(jsonString);

      toast({
        title: '导出成功',
        description: '模型数据已复制到剪贴板',
      });
    } catch (error) {
      console.error('导出数据失败:', error);
      toast({
        variant: 'destructive',
        title: '导出失败',
        description: '无法复制到剪贴板，请检查浏览器权限',
      });
    }
  };


  return (
    <div className="space-y-6 pb-8">
      {/* 页面头部 */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            模型详情
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            查看模型的完整信息、评估指标和可视化分析
          </p>
        </div>
        {/* 操作按钮组 */}
        {taskDetail && (
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={handlePredict} className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4" />
              <span className="hidden sm:inline">运行预测</span>
              <span className="sm:hidden">预测</span>
            </Button>
            <Button variant="outline" onClick={handleQuickBacktest} className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              <span className="hidden sm:inline">策略回测</span>
              <span className="sm:hidden">回测</span>
            </Button>
            <Button
              variant="outline"
              onClick={handleExportData}
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">数据导出</span>
              <span className="sm:hidden">导出</span>
            </Button>
          </div>
        )}
      </div>

      {/* 模型选择器 */}
      <Card>
        <CardHeader>
          <CardTitle>选择模型</CardTitle>
          <CardDescription>
            从已训练的模型中选择一个查看详细信息
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select
            value={selectedModelId}
            onValueChange={handleModelChange}
            disabled={loading}
          >
            <SelectTrigger>
              <SelectValue placeholder="请选择一个训练好的模型" />
            </SelectTrigger>
            <SelectContent>
              {models.length === 0 ? (
                <div className="p-4 text-center text-sm text-gray-500">
                  暂无可用模型，请先在AI实验室训练模型
                </div>
              ) : (
                models.map(model => (
                  <SelectItem key={String(model.id)} value={String(model.id)}>
                    {model.symbol} - {model.model_type.toUpperCase()} - {model.target_period}日
                    {model.trained_at && ` (${model.trained_at.substring(0, 10)})`}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* 错误提示 */}
      {error && (
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="p-4">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* 加载中状态 */}
      {loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              正在加载模型详情...
            </h3>
          </CardContent>
        </Card>
      )}

      {/* 模型详细信息 */}
      {taskDetail && !loading && (
        <div className="space-y-6">
          {/* 基本信息和评估指标 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 基本信息 */}
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
                  <span className="font-medium">{taskDetail.config?.symbol || 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">模型类型</span>
                  <span className="font-medium">
                    <span
                      className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded ${
                        taskDetail.config?.model_type === 'lightgbm'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                      }`}
                    >
                      {taskDetail.config?.model_type?.toUpperCase() || 'N/A'}
                    </span>
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">预测周期</span>
                  <span className="font-medium">{taskDetail.config?.target_period || 'N/A'}天</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">训练时间</span>
                  <span className="font-medium">
                    {taskDetail.completed_at?.replace(/(\d{4})-(\d{2})-(\d{2}).*/, '$1-$2-$3') || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">状态</span>
                  <span className={`font-medium ${
                    taskDetail.status === 'completed' ? 'text-green-600 dark:text-green-400' : ''
                  }`}>
                    {taskDetail.status === 'completed' ? '训练完成' : taskDetail.status}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* 训练指标 */}
            <Card>
              <CardHeader>
                <CardTitle>训练指标</CardTitle>
                <CardDescription>模型在测试集上的评估结果</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {taskDetail.metrics && Object.keys(taskDetail.metrics).length > 0 ? (
                  Object.entries(taskDetail.metrics).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center pb-2 border-b">
                      <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className={`font-mono font-medium ${
                        ['ic', 'rank_ic'].includes(key) ? 'text-blue-600 dark:text-blue-400' : ''
                      }`}>
                        {typeof value === 'number'
                          ? (key === 'samples' ? value.toLocaleString() : value.toFixed(4))
                          : String(value)}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400">暂无训练指标数据</div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* 回测指标 */}
          {(() => {
            const selectedModelData = models.find(m => String(m.id) === selectedModelId);
            const hasBacktestMetrics = selectedModelData?.backtest_metrics && (
              selectedModelData.backtest_metrics.rank_score !== null ||
              selectedModelData.backtest_metrics.annual_return !== null ||
              selectedModelData.backtest_metrics.sharpe_ratio !== null ||
              selectedModelData.backtest_metrics.max_drawdown !== null ||
              selectedModelData.backtest_metrics.win_rate !== null
            );

            return hasBacktestMetrics ? (
              <Card>
                <CardHeader>
                  <CardTitle>回测指标</CardTitle>
                  <CardDescription>模型策略在历史数据上的表现</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                    {selectedModelData.backtest_metrics?.rank_score !== null && selectedModelData.backtest_metrics?.rank_score !== undefined && (
                      <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
                        <div className="text-xs text-indigo-600 dark:text-indigo-400 mb-1">综合评分</div>
                        <div className="text-2xl font-bold text-indigo-900 dark:text-indigo-100">
                          {selectedModelData.backtest_metrics.rank_score.toFixed(2)}
                        </div>
                      </div>
                    )}
                    {selectedModelData.backtest_metrics?.annual_return !== null && selectedModelData.backtest_metrics?.annual_return !== undefined && (
                      <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                        <div className="text-xs text-green-600 dark:text-green-400 mb-1">年化收益</div>
                        <div className={`text-2xl font-bold ${
                          selectedModelData.backtest_metrics.annual_return >= 0
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}>
                          {selectedModelData.backtest_metrics.annual_return.toFixed(2)}%
                        </div>
                      </div>
                    )}
                    {selectedModelData.backtest_metrics?.sharpe_ratio !== null && selectedModelData.backtest_metrics?.sharpe_ratio !== undefined && (
                      <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                        <div className="text-xs text-amber-600 dark:text-amber-400 mb-1">夏普比率</div>
                        <div className="text-2xl font-bold text-amber-900 dark:text-amber-100">
                          {selectedModelData.backtest_metrics.sharpe_ratio.toFixed(2)}
                        </div>
                      </div>
                    )}
                    {selectedModelData.backtest_metrics?.max_drawdown !== null && selectedModelData.backtest_metrics?.max_drawdown !== undefined && (
                      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="text-xs text-red-600 dark:text-red-400 mb-1">最大回撤</div>
                        <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                          {selectedModelData.backtest_metrics.max_drawdown.toFixed(2)}%
                        </div>
                      </div>
                    )}
                    {selectedModelData.backtest_metrics?.win_rate !== null && selectedModelData.backtest_metrics?.win_rate !== undefined && (
                      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <div className="text-xs text-blue-600 dark:text-blue-400 mb-1">胜率</div>
                        <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                          {(selectedModelData.backtest_metrics.win_rate * 100).toFixed(2)}%
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : null;
          })()}

          {/* 训练配置 */}
          <Card>
            <CardHeader>
              <CardTitle>训练配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="space-y-1">
                  <div className="text-sm text-gray-600 dark:text-gray-400">数据范围</div>
                  <div className="font-medium">
                    {taskDetail.config?.start_date || 'N/A'} ~ {taskDetail.config?.end_date || 'N/A'}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-gray-600 dark:text-gray-400">训练集比例</div>
                  <div className="font-medium">
                    {((taskDetail.config?.train_ratio || 0.7) * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-gray-600 dark:text-gray-400">验证集比例</div>
                  <div className="font-medium">
                    {((taskDetail.config?.valid_ratio || 0.15) * 100).toFixed(0)}%
                  </div>
                </div>
                {taskDetail.config?.model_type === 'gru' && (
                  <>
                    <div className="space-y-1">
                      <div className="text-sm text-gray-600 dark:text-gray-400">序列长度</div>
                      <div className="font-medium">{taskDetail.config?.seq_length || 'N/A'}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-gray-600 dark:text-gray-400">批次大小</div>
                      <div className="font-medium">{taskDetail.config?.batch_size || 'N/A'}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-gray-600 dark:text-gray-400">训练轮数</div>
                      <div className="font-medium">{taskDetail.config?.epochs || 'N/A'}</div>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 特征重要性（LightGBM）或训练历史（GRU） */}
          {taskDetail.feature_importance && (
            <FeatureImportance />
          )}

          {taskDetail.training_history && (
            <TrainingHistory />
          )}
        </div>
      )}

      {/* 无模型选择时的提示 */}
      {!selectedModelId && !loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              请选择一个模型
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              在上方下拉框中选择一个模型以查看详细信息
            </p>
            {models.length === 0 && (
              <Button
                onClick={() => router.push('/ai-lab')}
                className="mt-4"
              >
                前往AI实验室训练模型
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function ModelDetailsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    }>
      <ModelDetailsPageContent />
    </Suspense>
  );
}
