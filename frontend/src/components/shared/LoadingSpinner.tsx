/**
 * 加载旋转器组件
 * 统一的加载状态指示器，支持多种尺寸和样式
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

export type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export type SpinnerVariant = 'border' | 'gradient' | 'dots';

interface LoadingSpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
  className?: string;
  text?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  xs: 'h-4 w-4',
  sm: 'h-5 w-5',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
  xl: 'h-16 w-16',
};

const LoadingSpinner = memo(function LoadingSpinner({
  size = 'md',
  variant = 'border',
  className,
  text
}: LoadingSpinnerProps) {
  const sizeClass = sizeClasses[size];

  const renderSpinner = () => {
    switch (variant) {
      case 'gradient':
        return (
          <div
            className={cn(
              'inline-block animate-spin rounded-full border-4 border-gray-300 border-t-blue-600',
              sizeClass,
              className
            )}
          />
        );

      case 'dots':
        return (
          <div className={cn('flex space-x-2', className)}>
            <div className={cn('animate-bounce rounded-full bg-blue-600', size === 'sm' ? 'h-2 w-2' : 'h-3 w-3')} />
            <div className={cn('animate-bounce rounded-full bg-blue-600', size === 'sm' ? 'h-2 w-2' : 'h-3 w-3')} style={{ animationDelay: '0.1s' }} />
            <div className={cn('animate-bounce rounded-full bg-blue-600', size === 'sm' ? 'h-2 w-2' : 'h-3 w-3')} style={{ animationDelay: '0.2s' }} />
          </div>
        );

      case 'border':
      default:
        return (
          <div
            className={cn(
              'animate-spin rounded-full border-b-2 border-primary',
              sizeClass,
              className
            )}
          />
        );
    }
  };

  if (text) {
    return (
      <div className="flex items-center justify-center">
        {renderSpinner()}
        <span className="ml-3 text-muted-foreground">{text}</span>
      </div>
    );
  }

  return renderSpinner();
});

LoadingSpinner.displayName = 'LoadingSpinner';

export default LoadingSpinner;
