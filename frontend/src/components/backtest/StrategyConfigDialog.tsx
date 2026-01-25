/**
 * 策略参数配置对话框
 * 显示策略参数编辑面板的对话框包装器
 */

'use client';

import { memo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import StrategyParamsPanel from '../StrategyParamsPanel';

interface StrategyConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId: string;
  strategyName: string;
  strategyParams: Record<string, any>;
  onParamsChange: (params: Record<string, any>) => void;
  onSave: (params: Record<string, any>) => void;
  onCancel: () => void;
}

const StrategyConfigDialog = memo(function StrategyConfigDialog({
  open,
  onOpenChange,
  strategyId,
  strategyName,
  strategyParams,
  onParamsChange,
  onSave,
  onCancel
}: StrategyConfigDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] sm:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-base sm:text-lg">
            {strategyName} - 参数配置
          </DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto py-2 sm:py-4 px-1">
          <StrategyParamsPanel
            strategyId={strategyId}
            onParamsChange={onParamsChange}
            isInDialog={true}
            initialParams={strategyParams}
            onSave={onSave}
            onCancel={onCancel}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
});

StrategyConfigDialog.displayName = 'StrategyConfigDialog';

export default StrategyConfigDialog;
