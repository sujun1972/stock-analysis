/**
 * 分页组件
 */

'use client';

import { memo } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalModels: number;
  onPageChange: (page: number) => void;
  isLoading: boolean;
}

const Pagination = memo(function Pagination({
  currentPage,
  totalPages,
  totalModels,
  onPageChange,
  isLoading
}: PaginationProps) {
  if (totalModels === 0) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        共 {totalModels} 个模型
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1 || isLoading}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          上一页
        </Button>
        <div className="text-sm text-gray-600 dark:text-gray-400">
          第 {currentPage} / {totalPages} 页
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages || isLoading}
        >
          下一页
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
});

export default Pagination;
