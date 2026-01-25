/**
 * 模型预测分析页面
 * 独立的预测分析工作台，支持选择模型、运行预测、查看结果
 */

'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMLStore } from '@/store/mlStore';
import PredictionChart from '@/components/ai-lab/PredictionChart';
import FeatureSnapshotViewer from '@/components/ai-lab/FeatureSnapshotViewer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Play, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

function PredictionPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { models, selectedModel, predictions, setSelectedModel, setPredictions, setModels } = useMLStore();

  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [loadingModels, setLoadingModels] = useState(false);

  // 加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      setLoadingModels(true);
      try {
        const response = await axios.get(`${API_BASE}/ml/models`, {
          params: { limit: 100 }
        });
        setModels(response.data.models || []);
      } catch (err) {
        console.error('加载模型列表失败:', err);
      } finally {
        setLoadingModels(false);
      }
    };

    // 如果models为空，加载模型列表
    if (models.length === 0) {
      loadModels();
    }
  }, [models.length, setModels]);

  // 初始化：从URL参数获取experimentId或modelId（兼容旧链接）
  useEffect(() => {
    const experimentIdFromUrl = searchParams.get('experimentId');
    const modelIdFromUrl = searchParams.get('modelId');

    if (experimentIdFromUrl && models.length > 0) {
      // 优先使用experimentId（新格式）
      setSelectedModelId(experimentIdFromUrl);
      const model = models.find(m => String(m.id) === experimentIdFromUrl);
      if (model) {
        setSelectedModel(model);
        runPrediction(experimentIdFromUrl);
      }
    } else if (modelIdFromUrl && models.length > 0) {
      // 向后兼容：使用model_id查找
      const model = models.find(m => m.model_id === modelIdFromUrl);
      if (model && model.id) {
        const experimentId = String(model.id);
        setSelectedModelId(experimentId);
        setSelectedModel(model);
        runPrediction(experimentId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, models]);

  // 运行预测
  const runPrediction = async (experimentId?: string) => {
    const targetExperimentId = experimentId || selectedModelId;

    if (!targetExperimentId) {
      setError('请先选择一个模型');
      return;
    }

    const model = models.find(m => String(m.id) === targetExperimentId);
    if (!model) {
      setError('找不到选中的模型');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 从模型的配置中获取日期范围，如果没有则使用默认值
      const config = model.config || {};
      const response = await axios.post(`${API_BASE}/ml/predict`, {
        experiment_id: model.id,  // 使用实验ID（新版）
        symbol: model.symbol,
        start_date: config.start_date || '2020-01-01',
        end_date: config.end_date || new Date().toISOString().split('T')[0],
      });

      if (response.data.predictions && response.data.predictions.length > 0) {
        setPredictions(response.data.predictions);
        setSelectedModel(model);
      } else {
        setError('预测结果为空');
      }
    } catch (err: any) {
      console.error('预测失败:', err);
      // 处理不同格式的错误信息
      let errorMessage = '预测失败，请重试';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // FastAPI 验证错误格式
          errorMessage = detail.map((e: any) => e.msg).join('; ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 处理模型选择变化
  const handleModelChange = (experimentId: string) => {
    setSelectedModelId(experimentId);
    setError('');
  };

  // 手动触发预测
  const handleRunPrediction = () => {
    runPrediction();
  };

  return (
    <div className="space-y-6 pb-8">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            模型预测分析
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            选择模型并生成预测，分析预测值与实际值的对比
          </p>
        </div>

        {/* 当前选中的模型信息 */}
        {selectedModel && predictions && predictions.length > 0 && (
          <div className="hidden md:flex items-center space-x-4 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <div className="text-sm">
              <div className="text-gray-500 dark:text-gray-400">当前模型</div>
              <div className="font-medium text-gray-700 dark:text-gray-300">
                {selectedModel.symbol} - {selectedModel.model_type.toUpperCase()}
              </div>
            </div>
            <div className="text-sm">
              <div className="text-gray-500 dark:text-gray-400">预测周期</div>
              <div className="text-gray-700 dark:text-gray-300">
                {selectedModel.target_period}日
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 模型选择和预测控制区 */}
      <Card>
        <CardHeader>
          <CardTitle>选择模型并运行预测</CardTitle>
          <CardDescription>
            从已训练的模型中选择一个，点击运行预测按钮生成预测结果
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-4">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                选择模型
              </label>
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
            </div>

            <Button
              onClick={handleRunPrediction}
              disabled={!selectedModelId || loading}
              className="px-6"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  预测中...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  运行预测
                </>
              )}
            </Button>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 预测结果展示区 */}
      {predictions && predictions.length > 0 ? (
        <div className="space-y-6">
          {/* 预测对比图 */}
          <PredictionChart />

          {/* 特征快照查看器 */}
          <FeatureSnapshotViewer />
        </div>
      ) : (
        !loading && (
          <Card>
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                暂无预测数据
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                请在上方选择一个模型，然后点击&quot;运行预测&quot;按钮生成预测结果
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
        )
      )}

      {/* 加载中状态 */}
      {loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              正在生成预测...
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              这可能需要几秒钟时间，请稍候
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function PredictionPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    }>
      <PredictionPageContent />
    </Suspense>
  );
}
