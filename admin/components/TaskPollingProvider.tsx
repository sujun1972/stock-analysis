'use client'

import { useTaskPolling } from '@/hooks/use-task-polling'

/**
 * 全局任务轮询提供者
 *
 * 在应用根组件中使用，确保任务轮询持续运行
 */
export function TaskPollingProvider({ children }: { children: React.ReactNode }) {
  useTaskPolling()

  return <>{children}</>
}
