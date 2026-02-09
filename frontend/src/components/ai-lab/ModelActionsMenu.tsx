/**
 * 模型操作菜单组件
 * 提供查看详情、运行预测、策略回测、删除模型等操作
 */

'use client';

import { memo } from 'react';
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

const ModelActionsMenu = memo(function ModelActionsMenu({
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
    // 跳转到回测页面,使用ml类型
    // id为model_id
    router.push(`/backtest?type=ml&id=${model.model_id}`);
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
});

export default ModelActionsMenu;
