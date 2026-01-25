/**
 * 模型表格筛选组件
 * 提供搜索、模型类型和来源筛选功能
 */

'use client';

import { memo } from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Search, RefreshCw } from 'lucide-react';

interface ModelTableFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  modelTypeFilter: string;
  onModelTypeChange: (value: string) => void;
  sourceFilter: string;
  onSourceChange: (value: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

const ModelTableFilters = memo(function ModelTableFilters({
  searchQuery,
  onSearchChange,
  modelTypeFilter,
  onModelTypeChange,
  sourceFilter,
  onSourceChange,
  isLoading,
  onRefresh
}: ModelTableFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-4">
      {/* 搜索框 */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          placeholder="搜索股票代码..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* 筛选器组 */}
      <div className="flex gap-2 items-center flex-wrap">
        {/* 模型类型筛选 */}
        <Select value={modelTypeFilter} onValueChange={onModelTypeChange}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="模型类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem value="lightgbm">LightGBM</SelectItem>
            <SelectItem value="gru">GRU</SelectItem>
          </SelectContent>
        </Select>

        {/* 来源筛选 */}
        <Select value={sourceFilter} onValueChange={onSourceChange}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="模型来源" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部来源</SelectItem>
            <SelectItem value="auto_experiment">自动实验</SelectItem>
            <SelectItem value="manual_training">手动训练</SelectItem>
          </SelectContent>
        </Select>

        {/* 刷新按钮 */}
        <Button variant="outline" size="icon" onClick={onRefresh} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    </div>
  );
});

export default ModelTableFilters;
