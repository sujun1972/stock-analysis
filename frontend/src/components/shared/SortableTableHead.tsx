/**
 * 可排序表格头组件
 * 提供点击排序功能和排序状态图标显示
 */

'use client';

import { memo, ReactNode } from 'react';
import { TableHead } from '@/components/ui/table';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export type SortOrder = 'asc' | 'desc' | null;

interface SortableTableHeadProps {
  children: ReactNode;
  field: string;
  currentSortField: string | null;
  currentSortOrder: SortOrder;
  onSort: (field: string) => void;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

const SortableTableHead = memo(function SortableTableHead({
  children,
  field,
  currentSortField,
  currentSortOrder,
  onSort,
  align = 'left',
  className
}: SortableTableHeadProps) {
  const isActive = currentSortField === field;

  const getSortIcon = () => {
    if (!isActive) {
      return <ArrowUpDown className="h-4 w-4 ml-1 text-gray-400" />;
    }
    return currentSortOrder === 'asc' ? (
      <ArrowUp className="h-4 w-4 ml-1 text-blue-600" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1 text-blue-600" />
    );
  };

  const alignClass = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
  }[align];

  const textAlignClass = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  }[align];

  return (
    <TableHead
      className={cn(
        textAlignClass,
        'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 select-none transition-colors',
        className
      )}
      onClick={() => onSort(field)}
    >
      <div className={cn('flex items-center', alignClass)}>
        {children}
        {getSortIcon()}
      </div>
    </TableHead>
  );
});

SortableTableHead.displayName = 'SortableTableHead';

export default SortableTableHead;
