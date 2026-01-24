/**
 * AI 策略实验舱主页面
 * 提供机器学习模型训练、预测和回测功能的可视化界面
 */

'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { useMLStore } from '@/store/mlStore';
import ModelTable from '@/components/ai-lab/ModelTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Rocket } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function AILabPage() {
  const router = useRouter();
  const { models, setModels } = useMLStore();
  const [loadingModels, setLoadingModels] = useState(true);

  // 加载模型列表
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await axios.get(`${API_BASE}/ml/models`, {
          params: { limit: 100 }
        });
        setModels(response.data.models || []);
      } catch (error) {
        console.error('加载模型列表失败:', error);
      } finally {
        setLoadingModels(false);
      }
    };

    loadModels();
  }, [setModels]);

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
        <Button
          size="lg"
          onClick={() => router.push('/auto-experiment')}
          className="flex items-center gap-2"
        >
          <Rocket className="h-5 w-5" />
          自动化实验
        </Button>
      </div>

      {/* 主内容区 - 只显示模型仓库 */}
      <div className="space-y-6">
        {models.length > 0 ? (
          // 有模型时显示模型表格
          <ModelTable />
        ) : (
          // 无模型时显示引导提示
          <Card>
            <CardContent className="p-12 text-center">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                开始训练您的第一个 AI 模型
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                您可以手动配置并训练单个模型，或使用自动化实验批量训练
              </p>
              <div className="flex gap-3 justify-center mb-8">
                <Button
                  variant="outline"
                  onClick={() => router.push('/auto-experiment')}
                  className="flex items-center gap-2"
                >
                  <Rocket className="h-4 w-4" />
                  自动化实验（推荐）
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8 text-left max-w-2xl mx-auto">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">数据驱动</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      自动获取60+技术指标和Alpha因子
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">智能预测</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      LightGBM和GRU深度学习模型
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">深度观察</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      特征重要性、快照查看器
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">一键回测</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      直接使用模型进行策略回测
                    </p>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
