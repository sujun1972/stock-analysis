/**
 * 模型详情页面
 * 展示模型的完整信息、评估指标、特征重要性/训练历史、训练配置等
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
import { PlayCircle, TrendingUp, Loader2, ArrowLeft } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

function ModelDetailsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { models, setModels, setSelectedModel, setCurrentTask } = useMLStore();

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


  return (
    <div className="space-y-6 pb-8">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/ai-lab')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              模型详情
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-2">
              查看模型的完整信息、评估指标和可视化分析
            </p>
          </div>
        </div>
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

            {/* 评估指标 */}
            <Card>
              <CardHeader>
                <CardTitle>评估指标</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">RMSE</span>
                  <span className="font-mono font-medium">
                    {taskDetail.metrics?.rmse?.toFixed(4) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">R²</span>
                  <span className="font-mono font-medium">
                    {taskDetail.metrics?.r2?.toFixed(4) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">IC</span>
                  <span className="font-mono font-medium text-blue-600 dark:text-blue-400">
                    {taskDetail.metrics?.ic?.toFixed(4) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Rank IC</span>
                  <span className="font-mono font-medium text-blue-600 dark:text-blue-400">
                    {taskDetail.metrics?.rank_ic?.toFixed(4) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-sm text-gray-600 dark:text-gray-400">样本数</span>
                  <span className="font-mono font-medium">
                    {taskDetail.metrics?.samples || 'N/A'}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

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

          {/* 操作按钮 */}
          <Card>
            <CardHeader>
              <CardTitle>操作</CardTitle>
              <CardDescription>
                使用此模型进行预测或回测
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                <Button onClick={handlePredict}>
                  <PlayCircle className="mr-2 h-4 w-4" />
                  运行预测
                </Button>
                <Button variant="outline" onClick={handleQuickBacktest}>
                  <TrendingUp className="mr-2 h-4 w-4" />
                  策略回测
                </Button>
              </div>
            </CardContent>
          </Card>
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
