/**
 * 训练监控视图
 * 显示实时训练进度和Loss曲线
 */

'use client';

import { memo } from 'react';
import { useMLStore } from '@/store/mlStore';

const TrainingMonitor = memo(function TrainingMonitor() {
  const { currentTask } = useMLStore();

  if (!currentTask) return null;

  const { status, progress, current_step, metrics } = currentTask;

  return (
    <div className="space-y-4">
      {/* 进度条 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">{current_step}</span>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {progress.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 状态 */}
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
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {current_step}
          </div>
        </div>

        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">完成度</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {progress.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* 训练指标（完成后显示） */}
      {metrics && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            性能指标
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">RMSE</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                {metrics.rmse?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">R²</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">
                {metrics.r2?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">IC</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {metrics.ic?.toFixed(4) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Rank IC</div>
              <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                {metrics.rank_ic?.toFixed(4) || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 错误信息 */}
      {status === 'failed' && currentTask.error_message && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="text-sm text-red-800 dark:text-red-200">
            <strong>错误：</strong> {currentTask.error_message}
          </div>
        </div>
      )}
    </div>
  );
});

export default TrainingMonitor;
