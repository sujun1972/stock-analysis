'use client'

import { Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { TaskPollingProvider } from '@/components/TaskPollingProvider'
import { ActiveTasksPanel } from '@/components/ActiveTasksPanel'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { queryClient } from '@/lib/react-query-config'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <ProtectedRoute requireAdmin>
        <TaskPollingProvider>
          <AdminLayout>
            {/* 使用 Suspense 包裹页面内容，提供加载状态 */}
            <Suspense fallback={<LoadingSkeleton />}>
              {children}
            </Suspense>
          </AdminLayout>
          {/* 全局活动任务面板 - 浮动在右下角 */}
          <ActiveTasksPanel />
        </TaskPollingProvider>
      </ProtectedRoute>
    </QueryClientProvider>
  )
}
