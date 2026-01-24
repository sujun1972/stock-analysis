/**
 * 模型预测详情页面
 * 显示预测值vs实际值对比图和特征快照查看器
 */

'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMLStore } from '@/store/mlStore';
import PredictionChart from '@/components/ai-lab/PredictionChart';
import FeatureSnapshotViewer from '@/components/ai-lab/FeatureSnapshotViewer';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

export default function PredictionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { selectedModel, predictions } = useMLStore();
  const modelId = params.modelId as string;

  useEffect(() => {
    // 如果没有选中的模型或模型ID不匹配，可能需要重新加载
    if (!selectedModel || selectedModel.model_id !== modelId) {
      console.warn('模型信息不匹配，可能需要重新加载');
    }
  }, [selectedModel, modelId]);

  return (
    <div className="space-y-6 pb-8">
      {/* 页面头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              模型预测分析
            </h1>
            {selectedModel && (
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                {selectedModel.symbol} - {selectedModel.model_type.toUpperCase()} -
                预测周期: {selectedModel.target_period}日
              </p>
            )}
          </div>
        </div>

        {/* 模型信息卡片 */}
        {selectedModel && (
          <div className="hidden md:flex items-center space-x-4 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <div className="text-sm">
              <div className="text-gray-500 dark:text-gray-400">模型ID</div>
              <div className="font-mono text-xs text-gray-700 dark:text-gray-300">
                {selectedModel.model_id.substring(0, 8)}...
              </div>
            </div>
            <div className="text-sm">
              <div className="text-gray-500 dark:text-gray-400">训练日期</div>
              <div className="text-gray-700 dark:text-gray-300">
                {selectedModel.trained_at?.substring(0, 10) || 'N/A'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className="space-y-6">
        {/* 预测对比图 */}
        <PredictionChart />

        {/* 特征快照查看器 */}
        <FeatureSnapshotViewer />

        {/* 如果没有预测数据，显示提示 */}
        {(!predictions || predictions.length === 0) && (
          <div className="p-12 text-center bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              暂无预测数据
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              请返回模型列表，点击"运行预测"按钮生成预测结果
            </p>
            <Button
              onClick={() => router.push('/ai-lab')}
              className="mt-4"
            >
              返回模型列表
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
