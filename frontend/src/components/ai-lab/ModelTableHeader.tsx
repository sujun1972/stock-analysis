/**
 * 模型表格头部组件
 * 提供列标题和排序功能
 */

'use client';

import { memo } from 'react';
import { TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface ModelTableHeaderProps {
  hasModels: boolean;
  allSelected: boolean;
  onToggleSelectAll: () => void;
  sortBy: string | null;
  sortOrder: 'asc' | 'desc';
  onSort: (field: string) => void;
}

const ModelTableHeader = memo(function ModelTableHeader({
  hasModels,
  allSelected,
  onToggleSelectAll,
  sortBy,
  sortOrder,
  onSort
}: ModelTableHeaderProps) {
  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="h-4 w-4 ml-1 text-gray-400" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="h-4 w-4 ml-1 text-blue-600" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1 text-blue-600" />
    );
  };

  return (
    <TableHeader>
      <TableRow>
        <TableHead className="w-[50px]">
          <Checkbox
            checked={allSelected}
            onCheckedChange={onToggleSelectAll}
            disabled={!hasModels}
            aria-label="全选"
          />
        </TableHead>
        <TableHead>模型信息</TableHead>
        <TableHead className="text-right">预测周期</TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('rmse')}>
          <div className="flex items-center justify-end">
            RMSE
            {getSortIcon('rmse')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('r2')}>
          <div className="flex items-center justify-end">
            R²
            {getSortIcon('r2')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('ic')}>
          <div className="flex items-center justify-end">
            IC
            {getSortIcon('ic')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('rank_ic')}>
          <div className="flex items-center justify-end">
            Rank IC
            {getSortIcon('rank_ic')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('rank_score')}>
          <div className="flex items-center justify-end">
            综合评分
            {getSortIcon('rank_score')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('annual_return')}>
          <div className="flex items-center justify-end">
            年化收益
            {getSortIcon('annual_return')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('sharpe_ratio')}>
          <div className="flex items-center justify-end">
            夏普比率
            {getSortIcon('sharpe_ratio')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('max_drawdown')}>
          <div className="flex items-center justify-end">
            最大回撤
            {getSortIcon('max_drawdown')}
          </div>
        </TableHead>
        <TableHead className="text-right cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" onClick={() => onSort('win_rate')}>
          <div className="flex items-center justify-end">
            胜率
            {getSortIcon('win_rate')}
          </div>
        </TableHead>
        <TableHead>训练时间</TableHead>
        <TableHead className="text-right">操作</TableHead>
      </TableRow>
    </TableHeader>
  );
});

export default ModelTableHeader;
