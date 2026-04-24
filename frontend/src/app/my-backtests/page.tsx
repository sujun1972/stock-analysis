'use client'

import { Suspense } from 'react'
import { Loader2 } from 'lucide-react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import BacktestHistoryContent from '@/components/backtest-history/BacktestHistoryContent'

/**
 * 我的回测页面
 * 展示用户的历史回测记录，支持查看详情、筛选、删除等操作
 * 需要登录才能访问
 */
export default function MyBacktestsPage() {
  return (
    <ProtectedRoute>
      <div className="container-custom py-8">
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">我的回测</h1>
          <p className="mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-400">
            查看和管理您的历史回测记录
          </p>
        </div>

        <Suspense
          fallback={
            <div className="min-h-[400px] flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          }
        >
          <BacktestHistoryContent />
        </Suspense>
      </div>
    </ProtectedRoute>
  )
}
