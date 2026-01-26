/**
 * 训练监控视图 V2
 * 支持Ridge基准对比结果显示
 */

'use client';

import { memo } from 'react';
import { useMLStore } from '@/store/mlStore';
import { ModelComparisonTable } from './ModelComparisonTable';
import { Badge } from '@/components/ui/badge';

const TrainingMonitorV2 = memo(function TrainingMonitorV2() {
  const { currentTask } = useMLStore();

  if (!currentTask) return null;

  const { status, progress, current_step, metrics, has_baseline } = currentTask;

  // 判断当前正在训练哪个模型
  const getCurrentModel = () => {
    if (!current_step) return null;
    if (current_step.includes('[Ridge]')) return 'Ridge';
    if (current_step.includes('[LightGBM]')) return 'LightGBM';
    return null;
  };

  const currentModel = getCurrentModel();

  return (
    <div className="space-y-4">
      {/* 进度条 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">{current_step}</span>
            {currentModel && (
              <Badge variant={currentModel === 'Ridge' ? 'default' : 'secondary'} className="text-xs">
                {currentModel}
              </Badge>
            )}
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {progress.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-300 ${
              currentModel === 'Ridge'
                ? 'bg-primary'
                : 'bg-blue-600'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 状态信息 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">状态</div>
          <div className={`text-sm font-medium ${
            status === 'running' ? 'text-green-600' :
            status === 'completed' ? 'text-blue-600' :
            status === 'failed' ? 'text-red-600' : 'text-yellow-600'
          }`}>
            {status === 'running' ? '训练中' :
             status === 'completed' ? '已完成' :
             status === 'failed' ? '失败' : '等待中'}
          </div>
        </div>

        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">当前阶段</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {current_step || '准备中...'}
          </div>
        </div>

        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">完成度</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {progress.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* LightGBM训练指标（总是显示） */}
      {metrics && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            LightGBM 性能指标
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">IC</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {(metrics.ic || metrics.test_ic)?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Rank IC</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {(metrics.rank_ic || metrics.test_rank_ic)?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">R²</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                {(metrics.r2 || metrics.test_r2)?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">MAE</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                {(metrics.mae || metrics.test_mae)?.toFixed(4) || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 模型对比表格（如果有Ridge基准） */}
      {has_baseline && status === 'completed' && (
        <ModelComparisonTable task={currentTask} />
      )}

      {/* 错误信息 */}
      {status === 'failed' && currentTask.error_message && (
        <div className="border-t border-red-200 dark:border-red-800 pt-4">
          <h3 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">
            错误信息
          </h3>
          <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded">
            {currentTask.error_message}
          </p>
        </div>
      )}
    </div>
  );
});

export default TrainingMonitorV2;
