/**
 * 回测提交按钮组件
 * 显示带加载状态和进度文本的提交按钮
 */

'use client';

import { memo } from 'react';
import { Button } from '@/components/ui/button';

interface SubmitButtonProps {
  isLoading: boolean;
  progress: string;
}

const SubmitButton = memo(function SubmitButton({ isLoading, progress }: SubmitButtonProps) {
  return (
    <Button
      type="submit"
      disabled={isLoading}
      className="w-full"
    >
      {isLoading ? (
        <span className="flex items-center justify-center">
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {progress || '运行中...'}
        </span>
      ) : (
        '运行回测'
      )}
    </Button>
  );
});

SubmitButton.displayName = 'SubmitButton';

export default SubmitButton;
