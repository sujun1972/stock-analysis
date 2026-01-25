/**
 * 指标卡片组件
 * 用于显示单个指标的标签和数值，支持多种样式变体
 */

'use client';

import { memo, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { HelpCircle } from 'lucide-react';

export type MetricCardVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
export type MetricCardSize = 'sm' | 'md' | 'lg';

interface MetricCardProps {
  label: string;
  value: string | number | ReactNode;
  variant?: MetricCardVariant;
  size?: MetricCardSize;
  tooltip?: string;
  icon?: ReactNode;
  className?: string;
  valueClassName?: string;
}

const variantClasses: Record<MetricCardVariant, string> = {
  default: 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-700',
  primary: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
  success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
  warning: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
  danger: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
  info: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800',
};

const labelColorClasses: Record<MetricCardVariant, string> = {
  default: 'text-gray-600 dark:text-gray-400',
  primary: 'text-blue-600 dark:text-blue-400',
  success: 'text-green-600 dark:text-green-400',
  warning: 'text-amber-600 dark:text-amber-400',
  danger: 'text-red-600 dark:text-red-400',
  info: 'text-indigo-600 dark:text-indigo-400',
};

const valueColorClasses: Record<MetricCardVariant, string> = {
  default: 'text-gray-900 dark:text-white',
  primary: 'text-blue-900 dark:text-blue-100',
  success: 'text-green-600 dark:text-green-400',
  warning: 'text-amber-900 dark:text-amber-100',
  danger: 'text-red-600 dark:text-red-400',
  info: 'text-indigo-900 dark:text-indigo-100',
};

const sizeClasses: Record<MetricCardSize, { container: string; label: string; value: string }> = {
  sm: {
    container: 'p-2',
    label: 'text-xs',
    value: 'text-sm',
  },
  md: {
    container: 'p-4',
    label: 'text-sm',
    value: 'text-2xl',
  },
  lg: {
    container: 'p-6',
    label: 'text-base',
    value: 'text-3xl',
  },
};

const MetricCard = memo(function MetricCard({
  label,
  value,
  variant = 'default',
  size = 'md',
  tooltip,
  icon,
  className,
  valueClassName
}: MetricCardProps) {
  const sizeClass = sizeClasses[size];
  const variantClass = variantClasses[variant];
  const labelColorClass = labelColorClasses[variant];
  const valueColorClass = valueColorClasses[variant];

  return (
    <div
      className={cn(
        'rounded-lg border hover:shadow-md transition-shadow',
        variantClass,
        sizeClass.container,
        className
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <span className={cn(sizeClass.label, labelColorClass)}>
            {label}
          </span>
        </div>
        {tooltip && (
          <div className="group relative">
            <HelpCircle className="h-4 w-4 text-gray-400 cursor-help" />
            <span className="invisible group-hover:visible absolute right-0 top-6 z-10 w-48 rounded bg-gray-900 px-2 py-1 text-xs text-white">
              {tooltip}
            </span>
          </div>
        )}
      </div>
      <div className={cn('font-bold', sizeClass.value, valueColorClass, valueClassName)}>
        {value}
      </div>
    </div>
  );
});

MetricCard.displayName = 'MetricCard';

export default MetricCard;
