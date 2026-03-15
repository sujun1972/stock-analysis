'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Code,
  User,
  Calendar,
  AlertTriangle,
  History,
  Send,
  Ban,
} from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function StrategyReviewPage() {
  const router = useRouter()
  const params = useParams()
  const strategyId = parseInt(params.id as string)

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [reviewHistory, setReviewHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 审核操作状态
  const [approving, setApproving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [unpublishing, setUnpublishing] = useState(false)
  const [approveComment, setApproveComment] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [autoEnable, setAutoEnable] = useState(true)
  const [showApproveForm, setShowApproveForm] = useState(false)
  const [showRejectForm, setShowRejectForm] = useState(false)

  // 加载策略详情
  const fetchStrategy = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.getStrategy(strategyId) as any
      if (response?.code === 200 && response.data) {
        setStrategy(response.data)
      } else {
        setError(response?.message || '加载失败')
      }
    } catch (error: any) {
      logger.error('获取策略详情失败', error)
      setError(error.response?.data?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [strategyId])

  // 加载审核历史
  const fetchReviewHistory = useCallback(async () => {
    try {
      const response: any = await apiClient.getStrategyReviewHistory(strategyId)
      if (Array.isArray(response)) {
        setReviewHistory(response)
      } else if (response.data && Array.isArray(response.data)) {
        setReviewHistory(response.data)
      }
    } catch (error) {
      logger.error('获取审核历史失败', error)
    }
  }, [strategyId])

  useEffect(() => {
    fetchStrategy()
    fetchReviewHistory()
  }, [fetchStrategy, fetchReviewHistory])

  // 批准策略
  const handleApprove = async () => {
    if (!strategy) return

    setApproving(true)
    try {
      await apiClient.approveStrategy(strategyId, {
        comment: approveComment || undefined,
        auto_enable: autoEnable,
      })

      alert(`策略 "${strategy.display_name}" 已批准发布${autoEnable ? '并启用' : ''}`)
      router.push('/strategies/pending-review')
    } catch (error: any) {
      alert(error.response?.data?.detail || '批准失败，请稍后重试')
    } finally {
      setApproving(false)
    }
  }

  // 拒绝策略
  const handleReject = async () => {
    if (!strategy) return
    if (!rejectReason.trim()) {
      alert('请输入拒绝原因')
      return
    }

    setRejecting(true)
    try {
      await apiClient.rejectStrategy(strategyId, {
        reason: rejectReason,
      })

      alert(`策略 "${strategy.display_name}" 已拒绝发布`)
      router.push('/strategies/pending-review')
    } catch (error: any) {
      alert(error.response?.data?.detail || '拒绝失败，请稍后重试')
    } finally {
      setRejecting(false)
    }
  }

  // 取消发布策略
  const handleUnpublish = async () => {
    if (!strategy) return

    if (!confirm(`确定要取消发布策略 "${strategy.display_name}" 吗？\n\n取消后策略将变为草稿状态，并自动禁用。用户需要重新申请发布。`)) {
      return
    }

    setUnpublishing(true)
    try {
      await apiClient.unpublishStrategy(strategyId)
      alert('策略已取消发布')
      // 刷新策略信息和审核历史
      await fetchStrategy()
      await fetchReviewHistory()
    } catch (error: any) {
      logger.error('取消发布失败', error)
      alert(error.response?.data?.detail || '取消发布失败，请稍后重试')
    } finally {
      setUnpublishing(false)
    }
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

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error || '策略不存在'}</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* 页面头部 */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-5 w-5" />
          返回
        </button>

        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">
                {strategy.display_name}
              </h1>
              <PublishStatusBadge status={strategy.publish_status as any} />
            </div>
            <p className="mt-1 text-sm text-gray-600">
              策略ID: #{strategy.id} | {strategy.name}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：策略详情 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 基本信息 */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">基本信息</h2>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">策略名称:</dt>
                <dd className="text-sm font-medium text-gray-900">{strategy.display_name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">策略标识:</dt>
                <dd className="text-sm font-mono text-gray-900">{strategy.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">策略类型:</dt>
                <dd className="text-sm text-gray-900">
                  {strategy.strategy_type === 'entry'
                    ? '入场策略'
                    : strategy.strategy_type === 'exit'
                    ? '离场策略'
                    : '选股策略'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">来源类型:</dt>
                <dd className="text-sm text-gray-900">
                  {strategy.source_type === 'builtin'
                    ? '系统内置'
                    : strategy.source_type === 'ai'
                    ? 'AI生成'
                    : '用户自定义'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">创建者:</dt>
                <dd className="text-sm text-gray-900">
                  {strategy.username || '系统'}
                  {strategy.user_id && ` (ID: ${strategy.user_id})`}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-600">申请时间:</dt>
                <dd className="text-sm text-gray-900">
                  {formatDate(strategy.publish_requested_at)}
                </dd>
              </div>
              {strategy.description && (
                <div>
                  <dt className="text-sm text-gray-600 mb-1">描述:</dt>
                  <dd className="text-sm text-gray-900">{strategy.description}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* 验证和风险信息 */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">验证和风险</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">验证状态:</span>
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
                    strategy.validation_status === 'passed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {strategy.validation_status === 'passed' ? '已通过' : strategy.validation_status}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">风险等级:</span>
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
                    strategy.risk_level === 'safe'
                      ? 'bg-green-100 text-green-800'
                      : strategy.risk_level === 'low'
                      ? 'bg-blue-100 text-blue-800'
                      : strategy.risk_level === 'medium'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {strategy.risk_level}
                </span>
              </div>
            </div>
          </div>

          {/* 策略代码 */}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">策略代码</h2>
              <Code className="h-5 w-5 text-gray-400" />
            </div>
            <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
              <code>{strategy.code}</code>
            </pre>
          </div>

          {/* 审核历史 */}
          {reviewHistory.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <div className="flex items-center gap-2 mb-4">
                <History className="h-5 w-5 text-gray-400" />
                <h2 className="text-lg font-semibold text-gray-900">审核历史</h2>
              </div>
              <div className="space-y-3">
                {reviewHistory.map((review) => (
                  <div key={review.id} className="border-l-2 border-gray-200 pl-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {review.action === 'approve' && '✅ 批准发布'}
                          {review.action === 'reject' && '❌ 拒绝发布'}
                          {review.action === 'withdraw' && '↩️ 撤回申请'}
                          {review.action === 'request_publish' && '📤 申请发布'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {review.reviewer_username || `用户 #${review.reviewer_id}`} ·{' '}
                          {formatDate(review.created_at)}
                        </p>
                        {review.comment && (
                          <p className="mt-1 text-sm text-gray-700">{review.comment}</p>
                        )}
                      </div>
                      <span className="text-xs text-gray-400">
                        {review.previous_status} → {review.new_status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右侧：操作面板 */}
        <div className="lg:col-span-1">
          <div className="sticky top-6 space-y-4">
            {/* 当前状态提示 */}
            {strategy.publish_status === 'pending_review' ? (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  此策略正在等待审核，请仔细审查代码和风险等级后做出决定。
                </AlertDescription>
              </Alert>
            ) : (
              <Alert>
                <AlertDescription>
                  此策略已处理，当前状态：
                  <PublishStatusBadge status={strategy.publish_status as any} className="ml-2" />
                </AlertDescription>
              </Alert>
            )}

            {/* 审核操作 */}
            {strategy.publish_status === 'pending_review' && (
              <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
                <h3 className="font-semibold text-gray-900">审核操作</h3>

                {!showApproveForm && !showRejectForm ? (
                  <div className="space-y-3">
                    <Button
                      onClick={() => setShowApproveForm(true)}
                      className="w-full bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      批准发布
                    </Button>
                    <Button
                      onClick={() => setShowRejectForm(true)}
                      variant="destructive"
                      className="w-full"
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      拒绝发布
                    </Button>
                  </div>
                ) : null}

                {/* 批准表单 */}
                {showApproveForm && (
                  <div className="space-y-4 border-t pt-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        审核意见（可选）
                      </label>
                      <Textarea
                        value={approveComment}
                        onChange={(e) => setApproveComment(e.target.value)}
                        placeholder="例如：策略质量良好，批准发布"
                        rows={3}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">自动启用策略</label>
                      <Switch checked={autoEnable} onCheckedChange={setAutoEnable} />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={handleApprove}
                        disabled={approving}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                      >
                        {approving ? '处理中...' : '确认批准'}
                      </Button>
                      <Button
                        onClick={() => setShowApproveForm(false)}
                        variant="outline"
                        disabled={approving}
                      >
                        取消
                      </Button>
                    </div>
                  </div>
                )}

                {/* 拒绝表单 */}
                {showRejectForm && (
                  <div className="space-y-4 border-t pt-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        拒绝原因 <span className="text-red-500">*</span>
                      </label>
                      <Textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="请详细说明拒绝的原因，帮助用户改进策略..."
                        rows={4}
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={handleReject}
                        disabled={rejecting || !rejectReason.trim()}
                        variant="destructive"
                        className="flex-1"
                      >
                        {rejecting ? '处理中...' : '确认拒绝'}
                      </Button>
                      <Button
                        onClick={() => setShowRejectForm(false)}
                        variant="outline"
                        disabled={rejecting}
                      >
                        取消
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 取消发布操作 */}
            {strategy.publish_status === 'approved' && (
              <div className="rounded-lg border border-orange-200 bg-orange-50 p-6 space-y-4">
                <h3 className="font-semibold text-orange-900">取消发布</h3>
                <p className="text-sm text-orange-700">
                  取消发布后，策略将变为草稿状态并被禁用，用户需要重新申请发布。
                </p>
                <Button
                  onClick={handleUnpublish}
                  disabled={unpublishing}
                  variant="outline"
                  className="w-full border-orange-300 text-orange-700 hover:bg-orange-100"
                >
                  <Ban className="h-4 w-4 mr-2" />
                  {unpublishing ? '处理中...' : '取消发布'}
                </Button>
              </div>
            )}

            {/* 快捷操作 */}
            <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
              <h3 className="font-semibold text-gray-900 mb-3">快捷操作</h3>
              <Button
                onClick={() => router.push(`/strategies/${strategy.id}`)}
                variant="outline"
                className="w-full"
              >
                <Code className="h-4 w-4 mr-2" />
                查看完整信息
              </Button>
              <Button
                onClick={() => router.push(`/strategies/${strategy.id}/edit`)}
                variant="outline"
                className="w-full"
              >
                编辑策略
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
