/**
 * 错误信息显示组件
 * 用于显示回测错误信息的提示框
 */

'use client';

import { memo } from 'react';

interface ErrorDisplayProps {
  error: string;
}

const ErrorDisplay = memo(function ErrorDisplay({ error }: ErrorDisplayProps) {
  if (!error) return null;

  return (
    <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
      <p className="text-sm text-destructive">{error}</p>
    </div>
  );
});

ErrorDisplay.displayName = 'ErrorDisplay';

export default ErrorDisplay;
