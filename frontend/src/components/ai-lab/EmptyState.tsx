/**
 * 空状态组件
 * 用于显示无数据时的引导界面
 */

'use client';

import { memo } from 'react';
import { Button } from '@/components/ui/button';
import { Rocket } from 'lucide-react';

interface EmptyStateProps {
  onStartTraining: () => void;
}

const EmptyState = memo(function EmptyState({ onStartTraining }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="text-center max-w-md">
        <Rocket className="h-16 w-16 mx-auto mb-4 text-gray-400" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          开始您的第一个模型训练
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          您还没有任何训练完成的模型。点击下方按钮开始训练您的第一个机器学习模型，开启量化交易之旅！
        </p>
        <Button size="lg" onClick={onStartTraining}>
          <Rocket className="h-5 w-5 mr-2" />
          开始训练模型
        </Button>
      </div>
    </div>
  );
});

export default EmptyState;
