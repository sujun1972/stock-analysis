/**
 * AI 策略实验舱主页面
 * 提供机器学习模型训练、预测和回测功能的可视化界面
 */

'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { useMLStore } from '@/store/mlStore';
import TrainingConfigPanel from '@/components/ai-lab/TrainingConfigPanel';
import TrainingMonitor from '@/components/ai-lab/TrainingMonitor';
import FeatureImportance from '@/components/ai-lab/FeatureImportance';
import TrainingHistory from '@/components/ai-lab/TrainingHistory';
import ModelTable from '@/components/ai-lab/ModelTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function AILabPage() {
  const { currentTask, models, setModels } = useMLStore();
  const [loadingModels, setLoadingModels] = useState(true);

  // 加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await axios.get(`${API_BASE}/ml/models`, {
          params: { limit: 100 }
        });
        setModels(response.data.models || []);
      } catch (error) {
        console.error('加载模型列表失败:', error);
      } finally {
        setLoadingModels(false);
      }
    };

    loadModels();
  }, [setModels]);

  return (
    <div className="space-y-6">
      {/* 页面标题和状态 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            AI 策略实验舱
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            可视化机器学习模型训练和预测
          </p>
        </div>

        {/* 任务状态指示 */}
        {currentTask && (
          <div className="flex items-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <div
              className={`h-3 w-3 rounded-full ${
                currentTask.status === 'running'
                  ? 'bg-green-500 animate-pulse'
                  : currentTask.status === 'completed'
                  ? 'bg-blue-500'
                  : currentTask.status === 'failed'
                  ? 'bg-red-500'
                  : 'bg-yellow-500'
              }`}
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {currentTask.current_step} ({currentTask.progress.toFixed(0)}%)
            </span>
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：配置面板 */}
          <div className="lg:col-span-1">
            <TrainingConfigPanel />
          </div>

          {/* 右侧：监控、可视化和模型列表 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 训练监控 */}
            {currentTask && currentTask.status === 'running' && <TrainingMonitor />}

            {/* 训练完成后显示模型特定的可视化 */}
            {currentTask && currentTask.status === 'completed' && (
              <>
                {/* LightGBM: 显示特征重要性 */}
                {currentTask.feature_importance && <FeatureImportance />}

                {/* GRU: 显示训练历史曲线 */}
                {currentTask.training_history && <TrainingHistory />}
              </>
            )}

            {/* 模型仓库：当没有训练任务或训练失败时显示 */}
            {(!currentTask || currentTask.status === 'failed') && (
              <>
                {models.length > 0 ? (
                  // 有模型时显示模型表格
                  <ModelTable />
                ) : (
                  // 无模型时显示引导提示
                  <Card>
                    <CardContent className="p-12 text-center">
                      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                        开始训练您的第一个 AI 模型
                      </h2>
                      <p className="text-gray-500 dark:text-gray-400 mb-8">
                        在左侧配置参数,点击&quot;开始训练&quot;按钮
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 text-left max-w-2xl mx-auto">
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
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
