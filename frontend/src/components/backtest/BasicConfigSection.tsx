/**
 * 回测基础配置区块
 * 包含股票代码、日期范围和初始资金的表单输入
 */

'use client';

import { memo } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { DatePicker } from '@/components/ui/date-picker';

interface BasicConfigSectionProps {
  symbols: string;
  onSymbolsChange: (value: string) => void;
  startDate: Date;
  onStartDateChange: (date: Date) => void;
  endDate: Date;
  onEndDateChange: (date: Date) => void;
  initialCash: number;
  onInitialCashChange: (value: number) => void;
}

const BasicConfigSection = memo(function BasicConfigSection({
  symbols,
  onSymbolsChange,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  initialCash,
  onInitialCashChange
}: BasicConfigSectionProps) {
  return (
    <div className="space-y-4 pb-4 border-b">
      {/* 股票代码 */}
      <div className="space-y-2">
        <Label htmlFor="symbols">股票代码</Label>
        <Input
          id="symbols"
          type="text"
          value={symbols}
          onChange={(e) => onSymbolsChange(e.target.value)}
          placeholder="600000 或 000031,600519"
          required
        />
        <p className="text-xs text-muted-foreground">
          支持单股或多股（逗号分隔），无需添加交易所后缀
        </p>
      </div>

      {/* 日期范围 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>开始日期</Label>
          <DatePicker
            date={startDate}
            onDateChange={(date) => date && onStartDateChange(date)}
            placeholder="选择开始日期"
          />
        </div>
        <div className="space-y-2">
          <Label>结束日期</Label>
          <DatePicker
            date={endDate}
            onDateChange={(date) => date && onEndDateChange(date)}
            placeholder="选择结束日期"
          />
        </div>
      </div>

      {/* 初始资金 */}
      <div className="space-y-2">
        <Label htmlFor="initialCash">
          初始资金: ¥{initialCash.toLocaleString()}
        </Label>
        <input
          id="initialCash"
          type="range"
          min="100000"
          max="10000000"
          step="100000"
          value={initialCash}
          onChange={(e) => onInitialCashChange(Number(e.target.value))}
          className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>10万</span>
          <span>1000万</span>
        </div>
      </div>
    </div>
  );
});

BasicConfigSection.displayName = 'BasicConfigSection';

export default BasicConfigSection;
