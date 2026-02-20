'use client'

import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute requireAdmin>
      <AdminLayout>
        {children}
      </AdminLayout>
    </ProtectedRoute>
  )
}
