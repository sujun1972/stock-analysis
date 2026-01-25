/**
 * 策略选择器组件
 * 显示可用策略列表，支持单选和打开参数配置对话框
 */

'use client';

import { memo } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Settings } from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  description: string;
  version: string;
  parameter_count: number;
}

interface StrategySelectorProps {
  strategies: Strategy[];
  selectedStrategyId: string;
  onStrategySelect: (strategyId: string) => void;
  onOpenConfig: (strategyId: string) => void;
}

const StrategySelector = memo(function StrategySelector({
  strategies,
  selectedStrategyId,
  onStrategySelect,
  onOpenConfig
}: StrategySelectorProps) {
  return (
    <div className="space-y-3">
      <Label>回测策略</Label>

      <div className="space-y-2">
        {strategies.map(strategy => (
          <div
            key={strategy.id}
            className={`p-3 border rounded-lg transition-colors ${
              selectedStrategyId === strategy.id
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            }`}
          >
            {/* 第一行: 单选框 + 名称 + 版本号 + 设置按钮 */}
            <div className="flex items-center justify-between gap-2">
              <div
                className="flex items-center gap-2 flex-1 cursor-pointer"
                onClick={() => onStrategySelect(strategy.id)}
              >
                <input
                  type="radio"
                  checked={selectedStrategyId === strategy.id}
                  onChange={() => onStrategySelect(strategy.id)}
                  className="text-blue-600"
                />
                <span className="font-medium text-gray-900 dark:text-white">
                  {strategy.name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  v{strategy.version}
                </span>
              </div>

              {/* 参数配置按钮 - 在第一行右侧 */}
              {strategy.parameter_count > 0 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    onStrategySelect(strategy.id);
                    onOpenConfig(strategy.id);
                  }}
                >
                  <Settings className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* 第二行: 参数数量标签 */}
            {strategy.parameter_count > 0 && (
              <div className="ml-6">
                <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-xs text-gray-600 dark:text-gray-400 rounded">
                  {strategy.parameter_count} 个参数
                </span>
              </div>
            )}

            {/* 第三行: 描述信息 */}
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 ml-6">
              {strategy.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
});

StrategySelector.displayName = 'StrategySelector';

export default StrategySelector;
export type { Strategy };
