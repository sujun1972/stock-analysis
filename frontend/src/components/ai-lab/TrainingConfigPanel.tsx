/**
 * 训练配置面板
 * 提供机器学习模型训练的参数配置界面
 */

'use client';

import { useState, useMemo } from 'react';
import { useMLStore } from '@/store/mlStore';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { DatePicker } from '@/components/ui/date-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { format, parse, isValid } from 'date-fns';
import { useToast } from '@/hooks/use-toast';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

interface TrainingConfigPanelProps {
  isInDialog?: boolean;
  onTrainingStart?: () => void;
}

export default function TrainingConfigPanel({ isInDialog = false, onTrainingStart }: TrainingConfigPanelProps = {}) {
  const { config, setConfig, setCurrentTask, setShowTrainingMonitor } = useMLStore();
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // 安全地解析日期，使用 useMemo 避免每次渲染都重新解析
  const startDate = useMemo(() => {
    const parsed = parse(config.start_date, 'yyyyMMdd', new Date());
    return isValid(parsed) ? parsed : undefined;
  }, [config.start_date]);

  const endDate = useMemo(() => {
    const parsed = parse(config.end_date, 'yyyyMMdd', new Date());
    return isValid(parsed) ? parsed : undefined;
  }, [config.end_date]);

  const handleStartTraining = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/ml/train`, config);
      const task = response.data;

      setCurrentTask(task);

      // 如果在弹窗中，只调用父组件的回调，不使用全局的 showTrainingMonitor
      if (isInDialog) {
        if (onTrainingStart) {
          onTrainingStart();
        }
      } else {
        // 如果不在弹窗中，使用原有的逻辑
        setShowTrainingMonitor(true);
      }

      // 开始轮询任务状态
      startPolling(task.task_id);
    } catch (error: any) {
      console.error('训练启动失败:', error);

      // 显示错误提示
      toast({
        variant: 'destructive',
        title: '训练启动失败',
        description: error.response?.data?.detail || '无法启动训练任务',
      });
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

            // 注意：训练完成和失败的 toast 由 ModelTable.tsx 统一处理
            // 通过监听 currentTask 状态变化显示，避免重复显示
          }
        }
      } catch (error) {
        console.error('轮询失败:', error);
        clearInterval(interval);
      }
    }, 2000); // 每2秒轮询一次
  };

  // 在弹窗模式下，不显示 Card 包装
  const content = (
    <div className="space-y-4">
        {/* 股票代码 */}
        <div className="space-y-2">
          <Label htmlFor="symbol">股票代码</Label>
          <Input
            id="symbol"
            type="text"
            value={config.symbol}
            onChange={(e) => setConfig({ symbol: e.target.value })}
            placeholder="000001"
          />
        </div>

        {/* 日期范围 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="start_date">开始日期</Label>
            <DatePicker
              date={startDate}
              onDateChange={(date) => {
                if (date) {
                  setConfig({ start_date: format(date, 'yyyyMMdd') });
                }
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="end_date">结束日期</Label>
            <DatePicker
              date={endDate}
              onDateChange={(date) => {
                if (date) {
                  setConfig({ end_date: format(date, 'yyyyMMdd') });
                }
              }}
            />
          </div>
        </div>

        {/* 模型类型 */}
        <div className="space-y-2">
          <Label htmlFor="model_type">模型类型</Label>
          <Select value={config.model_type} onValueChange={(value) => setConfig({ model_type: value as 'lightgbm' | 'gru' })}>
            <SelectTrigger id="model_type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="lightgbm">LightGBM（推荐）</SelectItem>
              <SelectItem value="gru">GRU（深度学习）</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 预测周期 */}
        <div className="space-y-2">
          <Label htmlFor="target_period">预测周期（天数）</Label>
          <Select value={config.target_period.toString()} onValueChange={(value) => setConfig({ target_period: parseInt(value) })}>
            <SelectTrigger id="target_period">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5">5日（短期）</SelectItem>
              <SelectItem value="10">10日（中期）</SelectItem>
              <SelectItem value="20">20日（月度）</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 特征缩放 */}
        <div className="space-y-2">
          <Label htmlFor="scaler_type">特征缩放方式</Label>
          <Select value={config.scaler_type} onValueChange={(value) => setConfig({ scaler_type: value as any })}>
            <SelectTrigger id="scaler_type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="robust">Robust（推荐LightGBM）</SelectItem>
              <SelectItem value="standard">Standard（推荐GRU）</SelectItem>
              <SelectItem value="minmax">MinMax</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 样本平衡 */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="balance_samples"
            checked={config.balance_samples}
            onCheckedChange={(checked) => setConfig({ balance_samples: checked as boolean })}
          />
          <Label
            htmlFor="balance_samples"
            className="text-sm font-normal cursor-pointer"
          >
            样本平衡（推荐GRU）
          </Label>
        </div>

        {config.balance_samples && (
          <div className="space-y-2">
            <Label htmlFor="balance_method">平衡方法</Label>
            <Select value={config.balance_method} onValueChange={(value) => setConfig({ balance_method: value as any })}>
              <SelectTrigger id="balance_method">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="undersample">欠采样（快）</SelectItem>
                <SelectItem value="smote">SMOTE（准确）</SelectItem>
                <SelectItem value="oversample">过采样</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* GRU特定参数 */}
        {config.model_type === 'gru' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              GRU 参数
            </h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="seq_length" className="text-xs">序列长度</Label>
                <Input
                  id="seq_length"
                  type="number"
                  value={config.seq_length}
                  onChange={(e) => setConfig({ seq_length: parseInt(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="epochs" className="text-xs">训练轮数</Label>
                <Input
                  id="epochs"
                  type="number"
                  value={config.epochs}
                  onChange={(e) => setConfig({ epochs: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>
        )}

        {/* 开始训练按钮 */}
        <Button
          onClick={handleStartTraining}
          disabled={loading}
          className="w-full"
          size="lg"
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
            '开始训练'
          )}
        </Button>
    </div>
  );

  // 如果在弹窗模式下，直接返回内容
  if (isInDialog) {
    return content;
  }

  // 否则返回带 Card 包装的内容
  return (
    <Card>
      <CardHeader>
        <CardTitle>训练配置</CardTitle>
      </CardHeader>
      <CardContent>
        {content}
      </CardContent>
    </Card>
  );
}
