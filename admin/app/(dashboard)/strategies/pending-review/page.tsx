'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Clock, User, Calendar, AlertCircle, Eye, CheckCircle, XCircle } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'

export default function PendingReviewStrategiesPage() {
  const router = useRouter()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // 获取待审核策略列表
  const fetchPendingStrategies = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.getPendingReviewStrategies({
        page: currentPage,
        page_size: 20,
      })

      if (response.success && response.data) {
        setStrategies(response.data)
        if (response.meta) {
          setTotalPages(response.meta.total_pages || 1)
          setTotalCount(response.meta.total || 0)
        }
      }
    } catch (error: any) {
      logger.error('获取待审核策略列表失败', error)
      setError(error.response?.data?.detail || '加载失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }, [currentPage])

  useEffect(() => {
    fetchPendingStrategies()
  }, [fetchPendingStrategies])

  // 查看策略详情（跳转到审核页面）
  const handleReview = (strategyId: number) => {
    router.push(`/strategies/${strategyId}/review`)
  }

  // 格式化时间
  const formatDate = (dateString?: string) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="p-6">
      {/* 页面头部 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">待审核策略</h1>
            <p className="mt-1 text-sm text-gray-600">
              查看所有等待审核的策略发布申请
            </p>
          </div>
        </div>
      </div>

      {/* 统计信息 - 仅在有待审核策略时显示 */}
      {!loading && totalCount > 0 && (
        <div className="mb-6 rounded-lg bg-yellow-50 border border-yellow-200 p-4">
          <div className="flex items-center gap-3">
            <Clock className="h-6 w-6 text-yellow-600" />
            <div>
              <p className="font-semibold text-yellow-900">
                当前共有 {totalCount} 个策略等待审核
              </p>
              <p className="text-sm text-yellow-700">
                请及时处理发布申请，避免用户等待时间过长
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* 策略列表 */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-gray-500">加载中...</div>
        </div>
      ) : strategies.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-gray-500">
          <CheckCircle className="mb-2 h-12 w-12 text-green-500" />
          <p className="text-lg font-medium">暂无待审核策略</p>
          <p className="mt-1 text-sm">所有策略已处理完毕</p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  {/* 左侧：策略信息 */}
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className="flex-1">
                        {/* 策略名称 */}
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {strategy.display_name}
                          </h3>
                          <PublishStatusBadge status={strategy.publish_status as any} size="sm" />
                          <span className="text-xs text-gray-500">#{strategy.id}</span>
                        </div>

                        {/* 策略描述 */}
                        {strategy.description && (
                          <p className="text-sm text-gray-600 mb-3">
                            {strategy.description}
                          </p>
                        )}

                        {/* 元信息 */}
                        <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <User className="h-4 w-4" />
                            <span>
                              {strategy.username || '系统'}
                              {strategy.user_id && ` (ID: ${strategy.user_id})`}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            <span>申请时间: {formatDate(strategy.publish_requested_at)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                              {strategy.strategy_type === 'entry' ? '入场策略' :
                               strategy.strategy_type === 'exit' ? '离场策略' : '选股策略'}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                              {strategy.source_type === 'builtin' ? '系统内置' :
                               strategy.source_type === 'ai' ? 'AI生成' : '用户自定义'}
                            </span>
                          </div>
                        </div>

                        {/* 验证和风险信息 */}
                        <div className="mt-3 flex gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-600">验证状态:</span>
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                              strategy.validation_status === 'passed'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {strategy.validation_status === 'passed' ? '已通过' : strategy.validation_status}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-600">风险等级:</span>
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                              strategy.risk_level === 'safe' ? 'bg-green-100 text-green-800' :
                              strategy.risk_level === 'low' ? 'bg-blue-100 text-blue-800' :
                              strategy.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {strategy.risk_level}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 右侧：操作按钮 */}
                  <div className="flex flex-col gap-2 ml-4">
                    <Button
                      onClick={() => handleReview(strategy.id)}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      审核
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <Button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                variant="outline"
              >
                上一页
              </Button>
              <span className="text-sm text-gray-600">
                第 {currentPage} / {totalPages} 页
              </span>
              <Button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                variant="outline"
              >
                下一页
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
