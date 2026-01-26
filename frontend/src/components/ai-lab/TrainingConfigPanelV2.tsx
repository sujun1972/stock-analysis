/**
 * 训练配置面板 V2
 * 支持多股池化训练和Ridge基准对比
 */

'use client';

import { useState, useMemo, memo } from 'react';
import { useMLStore } from '@/store/mlStore';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { DatePicker } from '@/components/ui/date-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { format, parse, isValid } from 'date-fns';
import { useToast } from '@/hooks/use-toast';
import { MultiStockSelector } from './MultiStockSelector';
import { Layers, Info } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

interface TrainingConfigPanelProps {
  isInDialog?: boolean;
  onTrainingStart?: () => void;
}

const TrainingConfigPanelV2 = memo(function TrainingConfigPanelV2({ isInDialog = false, onTrainingStart }: TrainingConfigPanelProps = {}) {
  const { config, setConfig, setCurrentTask, setShowTrainingMonitor } = useMLStore();
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // 池化训练模式
  const isPooledMode = config.enable_pooled_training && (config.symbols?.length || 0) > 1;

  // 安全地解析日期
  const startDate = useMemo(() => {
    const parsed = parse(config.start_date, 'yyyyMMdd', new Date());
    return isValid(parsed) ? parsed : undefined;
  }, [config.start_date]);

  const endDate = useMemo(() => {
    const parsed = parse(config.end_date, 'yyyyMMdd', new Date());
    return isValid(parsed) ? parsed : undefined;
  }, [config.end_date]);

  const handleStartTraining = async () => {
    // 验证配置
    if (config.enable_pooled_training && (!config.symbols || config.symbols.length < 2)) {
      toast({
        variant: 'destructive',
        title: '配置错误',
        description: '池化训练至少需要2只股票',
      });
      return;
    }

    setLoading(true);
    try {
      // 准备请求数据
      const requestData = {
        ...config,
        // 如果启用池化训练，使用symbols；否则使用symbol
        ...(config.enable_pooled_training
          ? { symbols: config.symbols, symbol: undefined }
          : { symbol: config.symbol, symbols: undefined }
        ),
      };

      const response = await axios.post(`${API_BASE}/ml/train`, requestData);
      const task = response.data;

      setCurrentTask(task);

      if (isInDialog) {
        if (onTrainingStart) {
          onTrainingStart();
        }
      } else {
        setShowTrainingMonitor(true);
      }

      // 开始轮询任务状态
      startPolling(task.task_id);

      toast({
        title: '训练已启动',
        description: isPooledMode
          ? `正在训练 ${config.symbols?.length} 只股票的池化模型`
          : '正在训练模型',
      });
    } catch (error: any) {
      console.error('训练启动失败:', error);

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
            useMLStore.getState().setShowFeatureImportance(true);
          }
        }
      } catch (error) {
        console.error('轮询失败:', error);
        clearInterval(interval);
      }
    }, 2000);
  };

  // 渲染配置内容
  const content = (
    <div className="space-y-4">
      {/* 池化训练模式开关 */}
      <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/30">
        <div className="flex items-center gap-3">
          <Layers className="h-5 w-5 text-primary" />
          <div>
            <Label htmlFor="enable_pooled_training" className="cursor-pointer">
              启用池化训练
            </Label>
            <p className="text-xs text-muted-foreground">
              使用多只股票数据进行联合训练，提升模型泛化能力
            </p>
          </div>
        </div>
        <Switch
          id="enable_pooled_training"
          checked={config.enable_pooled_training}
          onCheckedChange={(checked) => {
            setConfig({
              enable_pooled_training: checked,
              // 如果开启池化训练，默认启用Ridge基准
              enable_ridge_baseline: checked ? true : config.enable_ridge_baseline
            });
          }}
        />
      </div>

      {/* 股票选择 */}
      {config.enable_pooled_training ? (
        <>
          <MultiStockSelector
            symbols={config.symbols || []}
            onChange={(symbols) => setConfig({ symbols })}
            label="选择股票（池化训练）"
            maxSymbols={20}
          />
          {isPooledMode && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                池化训练将合并 {config.symbols?.length} 只股票的数据进行训练，
                总样本数预计增加 {config.symbols?.length}x
              </AlertDescription>
            </Alert>
          )}
        </>
      ) : (
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
      )}

      {/* Ridge基准对比 */}
      {config.enable_pooled_training && (
        <div className="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <Label htmlFor="enable_ridge_baseline" className="cursor-pointer">
              启用Ridge基准对比
            </Label>
            <p className="text-xs text-muted-foreground">
              同时训练Ridge线性模型作为基准，对比LightGBM性能
            </p>
          </div>
          <Switch
            id="enable_ridge_baseline"
            checked={config.enable_ridge_baseline}
            onCheckedChange={(checked) => setConfig({ enable_ridge_baseline: checked })}
          />
        </div>
      )}

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
            <SelectItem value="robust">Robust（推荐池化训练）</SelectItem>
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
        disabled={loading || (config.enable_pooled_training && (!config.symbols || config.symbols.length < 2))}
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
          <>
            {isPooledMode ? `开始池化训练 (${config.symbols?.length}只股票)` : '开始训练'}
          </>
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
});

export default TrainingConfigPanelV2;
