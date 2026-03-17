'use client'

import { Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { TaskPollingProvider } from '@/components/TaskPollingProvider'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { SystemConfigProvider } from '@/contexts'
import { queryClient } from '@/lib/react-query-config'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <ProtectedRoute requireAdmin>
        <SystemConfigProvider>
          <TaskPollingProvider>
            <AdminLayout>
              {/* 使用 Suspense 包裹页面内容，提供加载状态 */}
              <Suspense fallback={<LoadingSkeleton />}>
                {children}
              </Suspense>
            </AdminLayout>
          </TaskPollingProvider>
        </SystemConfigProvider>
      </ProtectedRoute>
    </QueryClientProvider>
  )
}
