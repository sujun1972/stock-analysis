/**
 * AI 策略实验舱主页面
 */

'use client';

import { useState, useEffect } from 'react';
import { useMLStore } from '@/store/mlStore';
import TrainingConfigPanel from '@/components/ai-lab/TrainingConfigPanel';
import TrainingMonitor from '@/components/ai-lab/TrainingMonitor';
import FeatureImportance from '@/components/ai-lab/FeatureImportance';
import PredictionChart from '@/components/ai-lab/PredictionChart';
import ModelList from '@/components/ai-lab/ModelList';
import FeatureSnapshotViewer from '@/components/ai-lab/FeatureSnapshotViewer';
import BacktestIntegration from '@/components/ai-lab/BacktestIntegration';

export default function AILabPage() {
  const { currentTask } = useMLStore();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 头部 */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                🧪 AI 策略实验舱
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                可视化机器学习模型训练和预测
              </p>
            </div>

            {/* 任务状态指示 */}
            {currentTask && (
              <div className="flex items-center space-x-2">
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
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：配置面板和模型列表 */}
          <div className="lg:col-span-1 space-y-6">
            <TrainingConfigPanel />
            <ModelList />
            <BacktestIntegration />
          </div>

          {/* 右侧：监控和可视化 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 训练监控 */}
            {currentTask && currentTask.status === 'running' && <TrainingMonitor />}

            {/* 训练完成后显示特征重要性 */}
            {currentTask && currentTask.status === 'completed' && currentTask.feature_importance && (
              <FeatureImportance />
            )}

            {/* 预测对比图 */}
            <PredictionChart />

            {/* 特征快照查看器 */}
            <FeatureSnapshotViewer />

            {/* 默认提示 */}
            {!currentTask && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
                <div className="text-6xl mb-4">🚀</div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  开始训练您的第一个 AI 模型
                </h2>
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  在左侧配置参数，点击&ldquo;开始训练&rdquo;按钮
                </p>
                <div className="grid grid-cols-2 gap-4 mt-8 text-left max-w-2xl mx-auto">
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div className="text-2xl mb-2">📊</div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      数据驱动
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      自动获取60+技术指标和Alpha因子
                    </div>
                  </div>
                  <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <div className="text-2xl mb-2">🤖</div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      智能预测
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      LightGBM和GRU深度学习模型
                    </div>
                  </div>
                  <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                    <div className="text-2xl mb-2">🔍</div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      深度观察
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      特征重要性、快照查看器
                    </div>
                  </div>
                  <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                    <div className="text-2xl mb-2">⚡</div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                      一键回测
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      直接使用模型进行策略回测
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
