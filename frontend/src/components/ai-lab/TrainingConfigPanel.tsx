/**
 * 训练配置面板
 */

'use client';

import { useState } from 'react';
import { useMLStore } from '@/store/mlStore';
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function TrainingConfigPanel() {
  const { config, setConfig, setCurrentTask, setShowTrainingMonitor } = useMLStore();
  const [loading, setLoading] = useState(false);

  const handleStartTraining = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/ml/train`, config);
      const task = response.data;

      setCurrentTask(task);
      setShowTrainingMonitor(true);

      // 开始轮询任务状态
      startPolling(task.task_id);
    } catch (error: any) {
      console.error('训练启动失败:', error);
      alert(error.response?.data?.detail || '训练启动失败');
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/ml/tasks/${taskId}`);
        const task = response.data;

        setCurrentTask(task);

        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(interval);

          if (task.status === 'completed') {
            setShowTrainingMonitor(false);
            // 显示特征重要性
            useMLStore.getState().setShowFeatureImportance(true);
          }
        }
      } catch (error) {
        console.error('轮询失败:', error);
        clearInterval(interval);
      }
    }, 2000); // 每2秒轮询一次
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        训练配置
      </h2>

      <div className="space-y-4">
        {/* 股票代码 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            股票代码
          </label>
          <input
            type="text"
            value={config.symbol}
            onChange={(e) => setConfig({ symbol: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            placeholder="000001"
          />
        </div>

        {/* 日期范围 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              开始日期
            </label>
            <input
              type="date"
              value={config.start_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
              onChange={(e) => setConfig({ start_date: e.target.value.replace(/-/g, '') })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              结束日期
            </label>
            <input
              type="date"
              value={config.end_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
              onChange={(e) => setConfig({ end_date: e.target.value.replace(/-/g, '') })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
          </div>
        </div>

        {/* 模型类型 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            模型类型
          </label>
          <select
            value={config.model_type}
            onChange={(e) => setConfig({ model_type: e.target.value as 'lightgbm' | 'gru' })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="lightgbm">LightGBM（推荐）</option>
            <option value="gru">GRU（深度学习）</option>
          </select>
        </div>

        {/* 预测周期 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            预测周期（天数）
          </label>
          <select
            value={config.target_period}
            onChange={(e) => setConfig({ target_period: parseInt(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="5">5日（短期）</option>
            <option value="10">10日（中期）</option>
            <option value="20">20日（月度）</option>
          </select>
        </div>

        {/* 特征缩放 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            特征缩放方式
          </label>
          <select
            value={config.scaler_type}
            onChange={(e) => setConfig({ scaler_type: e.target.value as any })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="robust">Robust（推荐LightGBM）</option>
            <option value="standard">Standard（推荐GRU）</option>
            <option value="minmax">MinMax</option>
          </select>
        </div>

        {/* 样本平衡 */}
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={config.balance_samples}
              onChange={(e) => setConfig({ balance_samples: e.target.checked })}
              className="rounded border-gray-300 dark:border-gray-600"
            />
            <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              样本平衡（推荐GRU）
            </span>
          </label>
        </div>

        {config.balance_samples && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              平衡方法
            </label>
            <select
              value={config.balance_method}
              onChange={(e) => setConfig({ balance_method: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="undersample">欠采样（快）</option>
              <option value="smote">SMOTE（准确）</option>
              <option value="oversample">过采样</option>
            </select>
          </div>
        )}

        {/* GRU特定参数 */}
        {config.model_type === 'gru' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              GRU 参数
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                  序列长度
                </label>
                <input
                  type="number"
                  value={config.seq_length}
                  onChange={(e) => setConfig({ seq_length: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                  训练轮数
                </label>
                <input
                  type="number"
                  value={config.epochs}
                  onChange={(e) => setConfig({ epochs: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* 开始训练按钮 */}
        <button
          onClick={handleStartTraining}
          disabled={loading}
          className={`w-full py-3 px-4 rounded-md font-medium text-white ${
            loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
          }`}
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              启动中...
            </span>
          ) : (
            '🚀 开始训练'
          )}
        </button>
      </div>
    </div>
  );
}
