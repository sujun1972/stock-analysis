'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { queryClient } from '@/lib/react-query-config'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <ProtectedRoute requireAdmin>
        <AdminLayout>
          {children}
        </AdminLayout>
      </ProtectedRoute>
    </QueryClientProvider>
  )
}
