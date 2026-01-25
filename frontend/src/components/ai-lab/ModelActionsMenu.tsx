/**
 * 模型操作菜单组件
 * 提供查看详情、运行预测、策略回测、删除模型等操作
 */

'use client';

import { useRouter } from 'next/navigation';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { MoreHorizontal, Info, PlayCircle, TrendingUp, Trash2 } from 'lucide-react';

interface ModelActionsMenuProps {
  model: {
    id: number;
    experiment_id?: number;
    model_id: string;
    symbol: string;
    config?: any;
  };
  onDelete?: (model: any) => void;
  triggerButton?: React.ReactNode;
  align?: 'start' | 'center' | 'end';
}

export default function ModelActionsMenu({
  model,
  onDelete,
  triggerButton,
  align = 'end'
}: ModelActionsMenuProps) {
  const router = useRouter();

  // 使用 experiment_id 或 id 作为唯一标识
  const experimentId = model.experiment_id || model.id;

  // 查看详情
  const handleViewDetails = () => {
    router.push(`/ai-lab/model-details?experimentId=${experimentId}`);
  };

  // 运行预测
  const handlePredict = () => {
    router.push(`/ai-lab/prediction?experimentId=${experimentId}`);
  };

  // 策略回测
  const handleQuickBacktest = () => {
    // 构建回测配置，使用模型训练时的日期范围
    const config = {
      strategyId: 'ml_model',
      symbols: model.symbol,
      startDate: model.config?.start_date || '2020-01-01',
      endDate: model.config?.end_date || new Date().toISOString().split('T')[0],
      initialCash: 100000,
      strategyParams: {
        model_id: model.model_id,
        buy_threshold: 0.15,  // 使用新的默认阈值
        sell_threshold: -0.3, // 使用新的默认阈值
        commission: 0.0003,
        slippage: 0.001,
        position_size: 1.0,
        stop_loss: 0.05,
        take_profit: 0.10,
      }
    };

    // 通过 URL 参数传递配置，回测页面将自动执行
    const configParam = encodeURIComponent(JSON.stringify(config));
    router.push(`/backtest?config=${configParam}`);
  };

  // 删除模型
  const handleDelete = () => {
    if (onDelete) {
      onDelete(model);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {triggerButton || (
          <Button variant="ghost" size="sm">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align}>
        <DropdownMenuItem onClick={handleViewDetails}>
          <Info className="mr-2 h-4 w-4" />
          查看详情
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handlePredict}>
          <PlayCircle className="mr-2 h-4 w-4" />
          运行预测
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleQuickBacktest}>
          <TrendingUp className="mr-2 h-4 w-4" />
          策略回测
        </DropdownMenuItem>
        {onDelete && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleDelete}
              className="text-red-600 dark:text-red-400"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              删除模型
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
