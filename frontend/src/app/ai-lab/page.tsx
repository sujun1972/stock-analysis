/**
 * AI 策略实验舱主页面
 * 提供机器学习模型训练、预测和回测功能的可视化界面
 */

'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Rocket, Plus } from 'lucide-react';

// 动态导入 ModelTable 组件以优化首屏加载
const ModelTable = dynamic(() => import('@/components/ai-lab/ModelTable'), {
  loading: () => (
    <div className="flex items-center justify-center h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg">
      <div className="text-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent motion-reduce:animate-[spin_1.5s_linear_infinite]" />
        <p className="mt-4 text-gray-600 dark:text-gray-300">加载模型列表...</p>
      </div>
    </div>
  )
});

export default function AILabPage() {
  const router = useRouter();
  const [showTrainingDialog, setShowTrainingDialog] = useState(false);

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            AI 策略实验舱
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            可视化机器学习模型训练和预测
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* 训练模型按钮 - 使用绿色背景 */}
          <Button
            size="lg"
            onClick={() => setShowTrainingDialog(true)}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white"
          >
            <Plus className="h-5 w-5" />
            训练模型
          </Button>
          {/* 自动化实验按钮 */}
          <Button
            size="lg"
            onClick={() => router.push('/auto-experiment')}
            className="flex items-center gap-2"
          >
            <Rocket className="h-5 w-5" />
            自动化实验
          </Button>
        </div>
      </div>

      {/* 主内容区 - 模型仓库表格 */}
      <ModelTable
        showTrainingDialog={showTrainingDialog}
        setShowTrainingDialog={setShowTrainingDialog}
      />
    </div>
  );
}
