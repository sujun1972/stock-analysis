/**
 * 特征快照查看器
 * 允许用户点击任意交易日，查看该日期所有特征的原始数值
 * 对于调试数据异常和理解模型决策非常有用
 */

'use client';

import { useState } from 'react';
import { useMLStore } from '@/stores/ml-store';
import axiosInstance from '@/lib/api/axios-instance'


interface FeatureSnapshot {
  date: string;
  features: Record<string, number>;
  target: number;
  prediction?: number;
}

export default function FeatureSnapshotViewer() {
  const { selectedModel, predictions } = useMLStore();
  const [selectedDate, setSelectedDate] = useState('');
  const [snapshot, setSnapshot] = useState<FeatureSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // 获取特征快照
  const loadSnapshot = async (date: string) => {
    if (!selectedModel) {
      alert('请先选择一个模型');
      return;
    }

    setLoading(true);
    try {
      // 调用后端API获取指定日期的特征数据
      const response = await axiosInstance.get(`/api/ml/features/snapshot`, {
        params: {
          symbol: selectedModel.symbol,
          date: date,
          model_id: selectedModel.model_id,
        },
      });

      setSnapshot(response.data);
      setIsModalOpen(true);
    } catch (error: any) {
      console.error('加载特征快照失败:', error);
      alert(`加载失败: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 从预测结果中选择日期
  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    loadSnapshot(date);
  };

  // 分类特征
  const categorizeFeatures = (features: Record<string, number>) => {
    const categories: Record<string, Record<string, number>> = {
      '基础行情': {},
      '移动平均线': {},
      '技术指标': {},
      'Alpha因子': {},
      '其他': {},
    };

    Object.entries(features).forEach(([key, value]) => {
      if (['open', 'high', 'low', 'close', 'volume', 'amount'].includes(key)) {
        categories['基础行情'][key] = value;
      } else if (key.startsWith('ma_') || key.startsWith('ema_')) {
        categories['移动平均线'][key] = value;
      } else if (
        key.startsWith('rsi_') ||
        key.startsWith('macd_') ||
        key.startsWith('kdj_') ||
        key.startsWith('boll_') ||
        key.startsWith('atr_') ||
        key.startsWith('cci_')
      ) {
        categories['技术指标'][key] = value;
      } else if (
        key.startsWith('momentum_') ||
        key.startsWith('reversal_') ||
        key.startsWith('volatility_') ||
        key.startsWith('volume_ratio_') ||
        key.startsWith('trend_')
      ) {
        categories['Alpha因子'][key] = value;
      } else {
        categories['其他'][key] = value;
      }
    });

    return categories;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        特征快照查看器
      </h2>

      {/* 日期选择 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          选择交易日
        </label>

        {predictions.length > 0 ? (
          <div className="grid grid-cols-5 gap-2 max-h-[200px] overflow-y-auto p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
            {predictions.map((pred) => (
              <button
                key={pred.date}
                onClick={() => handleDateSelect(pred.date)}
                className={`
                  px-3 py-2 text-xs rounded border transition-colors
                  ${selectedDate === pred.date
                    ? 'bg-blue-500 text-white border-blue-600'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                  }
                `}
              >
                {pred.date.replace(/(\d{4})(\d{2})(\d{2})/, '$2-$3')}
              </button>
            ))}
          </div>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            请先运行预测以查看可用日期
          </div>
        )}
      </div>

      {/* 快速说明 */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="text-sm text-blue-800 dark:text-blue-200">
          💡 <strong>使用提示：</strong> 点击任意交易日，查看该日期下 DataPipeline 生成的所有特征原始数值。
          对于调试数据异常（如股票停牌导致的 NaN）和理解模型决策非常有用。
        </div>
      </div>

      {/* 特征快照模态框 */}
      {isModalOpen && snapshot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* 标题栏 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  特征快照 - {snapshot.date}
                </h3>
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  股票: {selectedModel?.symbol} | 模型: {selectedModel?.model_type.toUpperCase()}
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl"
              >
                ×
              </button>
            </div>

            {/* 预测信息 */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">目标值（实际收益率）</div>
                  <div className={`text-lg font-bold ${snapshot.target > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                    {snapshot.target?.toFixed(2)}%
                  </div>
                </div>
                {snapshot.prediction !== undefined && (
                  <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">模型预测值</div>
                    <div className={`text-lg font-bold ${snapshot.prediction > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                      {snapshot.prediction?.toFixed(2)}%
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 特征列表 */}
            <div className="overflow-y-auto max-h-[calc(90vh-250px)] p-6">
              {Object.entries(categorizeFeatures(snapshot.features)).map(([category, features]) => {
                if (Object.keys(features).length === 0) return null;

                return (
                  <div key={category} className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 pb-2 border-b border-gray-200 dark:border-gray-600">
                      {category} ({Object.keys(features).length})
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(features).map(([key, value]) => (
                        <div
                          key={key}
                          className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
                        >
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 truncate" title={key}>
                            {key}
                          </div>
                          <div className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                            {isNaN(value) || !isFinite(value) ? (
                              <span className="text-red-500">异常值</span>
                            ) : (
                              value.toFixed(6)
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 底部操作栏 */}
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
              <div className="flex justify-between items-center">
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  共 {Object.keys(snapshot.features).length} 个特征
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-500"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 加载中提示 */}
      {loading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <div className="text-gray-900 dark:text-white font-medium">
                加载特征快照中...
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
