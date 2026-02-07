/**
 * 多选股票选择器
 * 支持手动输入和批量选择
 */

'use client';

import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';

interface MultiStockSelectorProps {
  symbols: string[];
  onChange: (symbols: string[]) => void;
  label?: string;
  placeholder?: string;
  maxSymbols?: number;
}

export function MultiStockSelector({
  symbols,
  onChange,
  label = '股票代码',
  placeholder = '输入股票代码后按回车添加',
  maxSymbols = 20
}: MultiStockSelectorProps) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');

  const handleAddSymbol = () => {
    const trimmed = inputValue.trim().toUpperCase();

    if (!trimmed) {
      setError('请输入股票代码');
      return;
    }

    // 验证股票代码格式 (6位数字)
    if (!/^\d{6}$/.test(trimmed)) {
      setError('股票代码必须是6位数字');
      return;
    }

    if (symbols.includes(trimmed)) {
      setError('该股票已添加');
      return;
    }

    if (symbols.length >= maxSymbols) {
      setError(`最多添加${maxSymbols}只股票`);
      return;
    }

    onChange([...symbols, trimmed]);
    setInputValue('');
    setError('');
  };

  const handleRemoveSymbol = (symbol: string) => {
    onChange(symbols.filter(s => s !== symbol));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddSymbol();
    }
  };

  const handleQuickAdd = (preset: string[]) => {
    const combined = [...symbols, ...preset];
    const newSymbols = Array.from(new Set(combined)).slice(0, maxSymbols);
    onChange(newSymbols);
  };

  // 预设股票池
  const quickPresets = {
    '银行股': ['600000', '600036', '601398', '601939', '601288'],
    '白酒股': ['600519', '000858', '000568', '600809', '000596'],
    '科技股': ['000063', '002415', '600584', '002230', '300059'],
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <span className="text-xs text-muted-foreground">
          {symbols.length}/{maxSymbols}
        </span>
      </div>

      {/* 已选择的股票 */}
      {symbols.length > 0 && (
        <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md min-h-[60px]">
          {symbols.map((symbol) => (
            <Badge
              key={symbol}
              variant="secondary"
              className="px-2 py-1 flex items-center gap-1"
            >
              {symbol}
              <button
                onClick={() => handleRemoveSymbol(symbol)}
                className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            setError('');
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={6}
          className={error ? 'border-destructive' : ''}
        />
        <Button
          onClick={handleAddSymbol}
          size="icon"
          variant="outline"
          disabled={symbols.length >= maxSymbols}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* 错误提示 */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* 快捷选择 */}
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">快捷选择</Label>
        <div className="flex flex-wrap gap-2">
          {Object.entries(quickPresets).map(([name, preset]) => (
            <Button
              key={name}
              onClick={() => handleQuickAdd(preset)}
              variant="outline"
              size="sm"
              className="text-xs h-7"
            >
              {name} ({preset.length}只)
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
