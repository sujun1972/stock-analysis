/**
 * 回测集成组件
 * 使用训练好的模型启动回测
 */

'use client';

import { useMLStore } from '@/store/mlStore';
import { useRouter } from 'next/navigation';

export default function BacktestIntegration() {
  const { selectedModel } = useMLStore();
  const router = useRouter();

  // 跳转到回测页面（使用ML模型对应的策略）
  const handleBacktest = () => {
    if (!selectedModel) {
      alert('请先选择一个模型');
      return;
    }

    // 跳转到回测页面,使用ml类型
    // id为model_id
    router.push(`/backtest?type=ml&id=${selectedModel.model_id}`);
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
              onClick={handleBacktest}
              className="w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              🚀 开始回测
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
