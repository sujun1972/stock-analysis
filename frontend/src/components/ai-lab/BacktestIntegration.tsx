/**
 * 回测集成组件
 * 一键使用训练好的模型启动回测
 */

'use client';

import { useState } from 'react';
import { useMLStore } from '@/store/mlStore';
import { useRouter } from 'next/navigation';
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function BacktestIntegration() {
  const { selectedModel } = useMLStore();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  // 一键回测
  const handleQuickBacktest = async () => {
    if (!selectedModel) {
      alert('请先选择一个模型');
      return;
    }

    setLoading(true);
    try {
      const config = selectedModel.config;

      // 创建回测任务
      const response = await axios.post(`${API_BASE}/backtest/run`, {
        symbol: selectedModel.symbol,
        start_date: config.start_date,
        end_date: config.end_date,
        initial_capital: 100000,

        // 使用ML模型信号作为策略
        strategy_type: 'ml_model',
        strategy_params: {
          model_id: selectedModel.model_id,
          model_type: selectedModel.model_type,
          target_period: selectedModel.target_period,

          // 交易阈值：预测上涨超过1%才买入，预测下跌超过-1%才卖出
          buy_threshold: 1.0,
          sell_threshold: -1.0,
        },

        // 交易设置
        commission: 0.0003,  // 万三佣金
        slippage: 0.001,     // 0.1% 滑点

        // 风控参数
        position_size: 1.0,  // 全仓
        stop_loss: 0.05,     // 5% 止损
        take_profit: 0.10,   // 10% 止盈
      });

      const backtestId = response.data.task_id || response.data.id;

      alert(`回测任务已创建！\n任务ID: ${backtestId}\n\n即将跳转到回测页面...`);

      // 跳转到回测页面
      router.push(`/backtest?task_id=${backtestId}`);

    } catch (error: any) {
      console.error('创建回测任务失败:', error);
      alert(`创建失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 高级回测（跳转到回测页面并预填参数）
  const handleAdvancedBacktest = () => {
    if (!selectedModel) {
      alert('请先选择一个模型');
      return;
    }

    // 跳转到回测页面，并通过URL参数传递模型信息
    const params = new URLSearchParams({
      model_id: selectedModel.model_id,
      symbol: selectedModel.symbol,
      model_type: selectedModel.model_type,
      start_date: selectedModel.config.start_date,
      end_date: selectedModel.config.end_date,
    });

    router.push(`/backtest?${params.toString()}`);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        策略回测
      </h2>

      {selectedModel ? (
        <div>
          {/* 选中模型信息 */}
          <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
              当前选中模型
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-blue-600 dark:text-blue-400">股票代码：</span>
                <span className="font-semibold text-gray-900 dark:text-white ml-1">
                  {selectedModel.symbol}
                </span>
              </div>
              <div>
                <span className="text-blue-600 dark:text-blue-400">模型类型：</span>
                <span className="font-semibold text-gray-900 dark:text-white ml-1">
                  {selectedModel.model_type.toUpperCase()}
                </span>
              </div>
              <div>
                <span className="text-blue-600 dark:text-blue-400">预测周期：</span>
                <span className="font-semibold text-gray-900 dark:text-white ml-1">
                  {selectedModel.target_period}天
                </span>
              </div>
              <div>
                <span className="text-blue-600 dark:text-blue-400">IC：</span>
                <span className="font-semibold text-gray-900 dark:text-white ml-1">
                  {selectedModel.metrics?.ic?.toFixed(4) || 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* 回测说明 */}
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              <div className="font-medium mb-2">📊 回测策略说明</div>
              <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                <li>• 使用模型预测值作为交易信号</li>
                <li>• 预测上涨 &gt; 1% 时买入，预测下跌 &lt; -1% 时卖出</li>
                <li>• 默认设置：10万初始资金，万三佣金，0.1%滑点</li>
                <li>• 风控：5%止损，10%止盈</li>
              </ul>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="space-y-3">
            <button
              onClick={handleQuickBacktest}
              disabled={loading}
              className="w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  创建回测中...
                </span>
              ) : (
                '🚀 一键回测（默认参数）'
              )}
            </button>

            <button
              onClick={handleAdvancedBacktest}
              className="w-full px-4 py-3 text-sm font-medium text-blue-600 dark:text-blue-400 border-2 border-blue-600 dark:border-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            >
              ⚙️ 高级回测（自定义参数）
            </button>
          </div>

          {/* 提示信息 */}
          <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <div className="text-xs text-yellow-800 dark:text-yellow-200">
              💡 <strong>提示：</strong> 回测结果仅供参考，不构成投资建议。
              实盘交易需要考虑更多因素，如市场流动性、交易延迟等。
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="mb-2">📋</div>
          <div className="text-sm">请先从模型仓库中选择一个模型</div>
        </div>
      )}
    </div>
  );
}
