'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { TaskPollingProvider } from '@/components/TaskPollingProvider'
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
            {children}
          </AdminLayout>
        </TaskPollingProvider>
      </ProtectedRoute>
    </QueryClientProvider>
  )
}
