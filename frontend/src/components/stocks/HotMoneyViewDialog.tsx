'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { AnalysisContent } from '@/components/stocks/analysis'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Save,
  Pencil,
  Trash2,
  X,
  Sparkles,
  Code,
  BookOpen,
  RotateCcw,
  Flame,
  TrendingUp,
  Gem,
  Brain,
  Database,
} from 'lucide-react'

import { AnalysisHistorySkeleton } from '@/components/shared/Skeleton'
import type { StockAnalysisRecord } from '@/types'

// ── 类型 ──────────────────────────────────────────────────────

export type AnalysisRecord = StockAnalysisRecord

// Tab 元信息：图标仅在 <sm（手机）显示，用于窄屏横向滚动时提升识别度
import type { LucideIcon } from 'lucide-react'
const DIALOG_TABS: { value: string; label: string; icon: LucideIcon }[] = [
  { value: 'hot_money', label: '游资', icon: Flame },
  { value: 'hot_money_review', label: '游资复盘', icon: RotateCcw },
  { value: 'midline', label: '中线', icon: TrendingUp },
  { value: 'midline_review', label: '中线复盘', icon: RotateCcw },
  { value: 'longterm', label: '价值', icon: Gem },
  { value: 'longterm_review', label: '价值复盘', icon: RotateCcw },
  { value: 'cio', label: 'CIO', icon: Brain },
  { value: 'data_collection', label: '数据', icon: Database },
]

export interface HotMoneyViewDialogProps {
  open: boolean
  onClose: () => void
  stockName: string
  stockCode: string   // 纯代码，如 000001
  tsCode: string      // ts_code，如 000001.SZ
  /** 打开时锁定到指定 Tab（hot_money/midline/longterm/cio/data_collection 或 *_review）。
   *  缺省时使用组件默认（hot_money）。主页"历史·"按钮按当前激活专家透传。 */
  defaultTab?: string
  // 游资观点提示词
  promptContent: string
  promptLoading: boolean
  // 数据收集提示词
  dataCollectionPrompt: string
  dataCollectionPromptLoading: boolean
  // 中线产业趋势专家观点
  midlinePrompt: string
  midlinePromptLoading: boolean
  // 长线价值守望者观点
  longtermPrompt: string
  longtermPromptLoading: boolean
  // 首席投资官（CIO）指令
  cioPrompt: string
  cioPromptLoading: boolean
  onSaved?: () => void
}


// ── 单个 Tab 内容（抽离为子组件） ──────────────────────────────

interface AnalysisTabProps {
  tsCode: string
  stockName?: string
  stockCode?: string
  analysisType: string
  templateKey?: string   // 用于 AI 直接生成，传入后显示"AI 分析"按钮
  promptContent: string
  promptLoading: boolean
  open: boolean
  refreshKey?: number    // 外部触发刷新（如一键分析完成后 +1）
  onSaved?: () => void
  enableReview?: boolean // 是否在每条记录上显示"复盘此报告"按钮
  reviewType?: 'hot_money' | 'midline' | 'longterm'  // 复盘类型，enableReview=true 时必填
  onReviewCreated?: (reviewType: 'hot_money' | 'midline' | 'longterm') => void
}

function AnalysisTab({
  tsCode, stockName, stockCode, analysisType, templateKey, promptContent, promptLoading, open, refreshKey, onSaved,
  enableReview, reviewType, onReviewCreated,
}: AnalysisTabProps) {
  const [copied, setCopied] = useState(false)
  const [promptExpanded, setPromptExpanded] = useState(false)

  const [history, setHistory] = useState<AnalysisRecord[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  // 源文本/渲染视图切换
  const [showRawText, setShowRawText] = useState(false)

  // 编辑状态
  const [editMode, setEditMode] = useState(false)
  const [editText, setEditText] = useState('')
  const [editScore, setEditScore] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editMsg, setEditMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 删除确认
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // 生成分析（数据收集 tab 专用）
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // AI 直接生成（游资观点 tab 专用）
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiGenMsg, setAiGenMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 复盘（enableReview 为 true 时显示按钮；每条历史记录可独立触发一次复盘）
  const [reviewing, setReviewing] = useState(false)
  const [reviewMsg, setReviewMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  const currentRecord: AnalysisRecord | null = history[currentIndex] ?? null

  useEffect(() => {
    if (!open || !tsCode) return
    setHistory([])
    setHistoryTotal(0)
    setCurrentIndex(0)
    setPromptExpanded(false)
    setCopied(false)
    setEditMode(false)
    setDeleteConfirm(false)
    setGenMsg(null)
    setAiGenMsg(null)

    setHistoryLoading(true)
    apiClient.getStockAnalysisHistory(tsCode, analysisType, 50, 0)
      .then((res) => {
        if (res?.code === 200 && res.data) {
          setHistory(res.data.items ?? [])
          setHistoryTotal(res.data.total ?? 0)
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoading(false))
  }, [open, tsCode, analysisType, refreshKey])

  // 切换记录时退出编辑模式
  useEffect(() => {
    setEditMode(false)
    setDeleteConfirm(false)
    setEditMsg(null)
    setShowRawText(false)
  }, [currentIndex])

  const reloadHistory = async () => {
    const histRes = await apiClient.getStockAnalysisHistory(tsCode, analysisType, 50, 0)
    if (histRes?.code === 200 && histRes.data) {
      setHistory(histRes.data.items ?? [])
      setHistoryTotal(histRes.data.total ?? 0)
      setCurrentIndex(0)
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(promptContent)
    } catch {
      const el = document.createElement('textarea')
      el.value = promptContent
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleGenerate = async () => {
    if (!tsCode || !stockName) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const res = await apiClient.collectStockData(tsCode, stockName)
      if (res?.code === 200 && res.data?.text) {
        setGenMsg({ text: '数据收集完成', type: 'success' })
        await reloadHistory()
        onSaved?.()
      } else {
        setGenMsg({ text: res?.message || '数据收集失败', type: 'error' })
      }
    } catch (e: any) {
      setGenMsg({ text: e?.response?.data?.message || '数据收集失败', type: 'error' })
    } finally {
      setGenerating(false)
    }
  }

  const handleAiGenerate = async () => {
    if (!tsCode || !stockName || !stockCode || !templateKey) return
    setAiGenerating(true)
    setAiGenMsg(null)
    try {
      const res = await apiClient.generateStockAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        analysis_type: analysisType,
        template_key: templateKey,
      })
      if (res?.code === 200 && res.data?.analysis_text) {
        setAiGenMsg({ text: 'AI 分析完成，已自动保存', type: 'success' })
        await reloadHistory()
        onSaved?.()
      } else {
        setAiGenMsg({ text: res?.message || 'AI 分析失败', type: 'error' })
      }
    } catch (e: any) {
      setAiGenMsg({ text: e?.response?.data?.message || 'AI 分析失败', type: 'error' })
    } finally {
      setAiGenerating(false)
    }
  }

  const handleReview = async (force = false) => {
    if (!currentRecord || !tsCode || !stockName || !stockCode || !reviewType) return
    setReviewing(true)
    setReviewMsg(null)

    // 失败统一处理：若后端返回带"建议..."的时间窗不足提示且非 force，弹 confirm 询问强制重试
    const handleFailure = async (backendMsg: string) => {
      if (backendMsg.includes('建议') && !force) {
        if (window.confirm(`${backendMsg}\n\n是否仍要强制生成复盘？`)) {
          await handleReview(true)
          return
        }
        setReviewMsg({ text: '已取消复盘', type: 'error' })
      } else {
        setReviewMsg({ text: backendMsg, type: 'error' })
      }
    }

    try {
      const res = await apiClient.generateReviewAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        original_analysis_id: currentRecord.id,
        review_type: reviewType,
        force,
      })
      if (res?.code === 200 && res.data?.analysis_text) {
        setReviewMsg({ text: '复盘完成，已切换到复盘 Tab', type: 'success' })
        onReviewCreated?.(reviewType)
      } else {
        await handleFailure(res?.message || '复盘失败')
      }
    } catch (e: any) {
      await handleFailure(e?.response?.data?.message || '复盘失败')
    } finally {
      setReviewing(false)
    }
  }

  const handleEditStart = () => {
    if (!currentRecord) return
    setEditText(currentRecord.analysis_text)
    setEditScore(currentRecord.score !== null ? String(currentRecord.score) : '')
    setEditMsg(null)
    setEditMode(true)
  }

  const handleEditCancel = () => {
    setEditMode(false)
    setEditMsg(null)
  }

  const handleEditSave = async () => {
    if (!currentRecord) return
    if (!editText.trim()) {
      setEditMsg({ text: '请输入分析内容', type: 'error' })
      return
    }
    const score = editScore.trim() ? parseFloat(editScore) : undefined
    if (score !== undefined && (isNaN(score) || score < 0 || score > 10)) {
      setEditMsg({ text: '评分需在 0-10 之间', type: 'error' })
      return
    }
    setEditSaving(true)
    setEditMsg(null)
    try {
      const res = await apiClient.updateStockAnalysis(currentRecord.id, {
        analysis_text: editText.trim(),
        score,
      })
      if (res?.code === 200) {
        setEditMode(false)
        await reloadHistory()
        onSaved?.()
      } else {
        setEditMsg({ text: res?.message || '修改失败', type: 'error' })
      }
    } catch (e: any) {
      setEditMsg({ text: e?.response?.data?.message || '修改失败', type: 'error' })
    } finally {
      setEditSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!currentRecord) return
    setDeleting(true)
    try {
      const res = await apiClient.deleteStockAnalysis(currentRecord.id)
      if (res?.code === 200) {
        setDeleteConfirm(false)
        await reloadHistory()
        onSaved?.()
      }
    } catch {
      // ignore
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* 历史记录区 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            已保存分析
            {historyTotal > 0 && (
              <span className="ml-1.5 text-xs text-gray-500 dark:text-gray-400">（共 {historyTotal} 条）</span>
            )}
          </span>
          <div className="flex items-center gap-2">
            {analysisType === 'stock_data_collection' && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerate}
                disabled={generating}
                className="gap-1.5 h-7 text-xs"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {generating ? '收集中...' : '生成分析'}
              </Button>
            )}
            {templateKey && (
              <Button
                onClick={handleAiGenerate}
                disabled={aiGenerating}
                size="sm"
                variant="outline"
                className="gap-1.5 h-7 text-xs"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {aiGenerating ? 'AI 分析中...' : 'AI 分析'}
              </Button>
            )}
            {history.length > 1 && (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentIndex((i) => Math.min(i + 1, history.length - 1))}
                  disabled={currentIndex >= history.length - 1}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                  title="更早版本"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-gray-600 dark:text-gray-400 min-w-[60px] text-center">
                  第 {currentIndex + 1} / {history.length} 条
                </span>
                <button
                  onClick={() => setCurrentIndex((i) => Math.max(i - 1, 0))}
                  disabled={currentIndex <= 0}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                  title="更新版本"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
        {genMsg && (
          <p className={`text-xs mb-2 ${genMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {genMsg.text}
          </p>
        )}
        {aiGenMsg && (
          <p className={`text-xs mb-2 ${aiGenMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {aiGenMsg.text}
          </p>
        )}
        {reviewMsg && (
          <p className={`text-xs mb-2 ${reviewMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {reviewMsg.text}
          </p>
        )}

        {historyLoading ? (
          <AnalysisHistorySkeleton />
        ) : currentRecord ? (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
            {/* 记录头部：版本信息 + 操作按钮 */}
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>
                版本 {currentRecord.version} · {new Date(currentRecord.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
              </span>
              <div className="flex items-center gap-2">
                {currentRecord.score !== null && !editMode && (
                  <span className={`font-semibold px-2 py-0.5 rounded text-sm ${
                    currentRecord.score >= 8 ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                    : currentRecord.score >= 6 ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                  }`}>
                    评分 {currentRecord.score}
                  </span>
                )}
                {!editMode && !deleteConfirm && (
                  <>
                    {enableReview && reviewType && (
                      <button
                        onClick={() => handleReview(false)}
                        disabled={reviewing}
                        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-orange-500 dark:hover:text-orange-400 disabled:opacity-40"
                        title={`让${reviewType === 'hot_money' ? '短线' : reviewType === 'midline' ? '中线' : '长线'}专家复盘此报告`}
                      >
                        <RotateCcw className={`h-3.5 w-3.5 ${reviewing ? 'animate-spin' : ''}`} />
                      </button>
                    )}
                    <button
                      onClick={() => setShowRawText(!showRawText)}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-purple-500 dark:hover:text-purple-400"
                      title={showRawText ? '渲染视图' : '源文本'}
                    >
                      {showRawText ? <BookOpen className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
                    </button>
                    <button
                      onClick={handleEditStart}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-blue-500 dark:hover:text-blue-400"
                      title="编辑"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(true)}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400"
                      title="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* 删除确认 */}
            {deleteConfirm && !editMode && (
              <div className="flex items-center gap-2 py-1">
                <span className="text-xs text-red-500">确定删除这条记录？</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="text-xs px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                >
                  {deleting ? '删除中...' : '确定'}
                </button>
                <button
                  onClick={() => setDeleteConfirm(false)}
                  className="text-xs px-2 py-0.5 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  取消
                </button>
              </div>
            )}

            {/* 编辑模式 */}
            {editMode ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 dark:text-gray-300">评分（可选）</span>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    step={0.1}
                    value={editScore}
                    onChange={(e) => setEditScore(e.target.value)}
                    placeholder="0-10"
                    className="w-20 h-7 text-xs border border-gray-200 dark:border-gray-600 rounded px-2 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                  />
                </div>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={6}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg p-3 resize-none bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {editMsg && (
                  <p className={`text-xs ${editMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                    {editMsg.text}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleEditSave}
                    disabled={editSaving || !editText.trim()}
                    size="sm"
                    className="gap-1.5"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {editSaving ? '保存中...' : '保存修改'}
                  </Button>
                  <Button
                    onClick={handleEditCancel}
                    disabled={editSaving}
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                  >
                    <X className="h-3.5 w-3.5" />
                    取消
                  </Button>
                </div>
              </div>
            ) : showRawText ? (
              <pre className="whitespace-pre-wrap text-sm font-mono break-words text-gray-800 dark:text-gray-200 leading-relaxed">
                {currentRecord.analysis_text}
              </pre>
            ) : (
              <AnalysisContent text={currentRecord.analysis_text} analysisType={analysisType} />
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500 dark:text-gray-400 text-sm border border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
            暂无保存记录，点击上方按钮生成分析
          </div>
        )}
      </div>

      {/* 提示词（可折叠，复制按钮在内） */}
      <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPromptExpanded((v) => !v)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {promptExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            提示词
          </button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={promptLoading || !promptContent}
            className="gap-1.5 h-7 text-xs"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? '已复制' : '复制提示词'}
          </Button>
        </div>
        {promptExpanded && (
          <div className="mt-2">
            {promptLoading ? (
              <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">加载中...</div>
            ) : (
              <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 leading-relaxed font-mono max-h-60 overflow-y-auto">
                {promptContent}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── 主弹窗组件 ──────────────────────────────────────────────────

export function HotMoneyViewDialog({
  open, onClose, stockName, stockCode, tsCode, defaultTab,
  promptContent, promptLoading,
  dataCollectionPrompt, dataCollectionPromptLoading,
  midlinePrompt, midlinePromptLoading,
  longtermPrompt, longtermPromptLoading,
  cioPrompt, cioPromptLoading,
  onSaved,
}: HotMoneyViewDialogProps) {
  const [multiGenerating, setMultiGenerating] = useState(false)
  const [multiMsg, setMultiMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [activeTab, setActiveTab] = useState(defaultTab ?? 'hot_money')

  // 弹窗关闭时重置；打开时若有 defaultTab 则锁定到指定 Tab
  useEffect(() => {
    if (!open) {
      setMultiGenerating(false)
      setMultiMsg(null)
      setActiveTab(defaultTab ?? 'hot_money')
    } else if (defaultTab) {
      setActiveTab(defaultTab)
    }
  }, [open, defaultTab])

  const handleReviewCreated = useCallback((reviewType: 'hot_money' | 'midline' | 'longterm') => {
    setRefreshKey((k) => k + 1)
    const targetTab = reviewType === 'hot_money' ? 'hot_money_review'
      : reviewType === 'midline' ? 'midline_review'
      : 'longterm_review'
    setActiveTab(targetTab)
    onSaved?.()
  }, [onSaved])

  const handleMultiGenerate = useCallback(async () => {
    if (!tsCode || !stockName || !stockCode) return
    setMultiGenerating(true)
    setMultiMsg(null)
    try {
      const res = await apiClient.generateMultiAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        analysis_types: ['hot_money_view', 'midline_industry_expert', 'longterm_value_watcher'],
        include_cio: true,
      })
      if (res?.code === 200) {
        const data = res.data
        const count = data?.expert_count ?? 0
        const errors = data?.errors?.length ?? 0
        const time = data?.total_generation_time ?? 0
        setMultiMsg({
          text: `${count} 个专家分析完成（${time}s）` + (errors ? `，${errors} 个失败` : ''),
          type: errors ? 'error' : 'success',
        })
        setRefreshKey((k) => k + 1)
        onSaved?.()
      } else {
        setMultiMsg({ text: res?.message || '一键分析失败', type: 'error' })
      }
    } catch (e: any) {
      setMultiMsg({ text: e?.response?.data?.message || '一键分析失败', type: 'error' })
    } finally {
      setMultiGenerating(false)
    }
  }, [tsCode, stockName, stockCode, onSaved])

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      {/*
        DialogContent 在 <sm（手机）切换为全屏 Sheet：
        - inset-0 + 100dvh：占满视口；translate-*-0 取消默认居中偏移
        - rounded-none + border-0：去掉桌面弹窗的卡片边框
        - slide-in/out-to-bottom：从底部滑入/滑出（复用 tailwindcss-animate）
        - p-0/gap-0：让内部区块自控 padding，便于 Footer 吸底 + Header 对齐
        ≥sm 保持原居中弹窗样式（max-w-[720px] + p-6）。
      */}
      <DialogContent
        className="flex flex-col gap-0 p-0 max-sm:inset-0 max-sm:left-0 max-sm:top-0 max-sm:h-[100dvh] max-sm:max-h-[100dvh] max-sm:w-screen max-sm:max-w-none max-sm:translate-x-0 max-sm:translate-y-0 max-sm:rounded-none max-sm:border-0 max-sm:data-[state=closed]:slide-out-to-bottom max-sm:data-[state=open]:slide-in-from-bottom sm:max-w-[720px] sm:max-h-[90vh] sm:p-6 sm:gap-4"
      >
        <DialogHeader className="shrink-0 px-4 pt-4 pb-2 sm:p-0">
          <DialogTitle>AI 分析：{stockName}（{stockCode}）</DialogTitle>
          <DialogDescription>保存并回顾每次 AI 分析结果</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          {/* 窄屏横向滚动 + 图标提示；≥sm 恢复 8 列均分网格。
              `scroll-shadow-x` 在 <sm 的两端渲染渐变遮罩，告诉用户"可左右滑动" */}
          <div className="shrink-0 mx-4 sm:mx-0 sm:contents scroll-shadow-x">
            <TabsList
              className="flex w-auto sm:w-full sm:grid sm:grid-cols-8 justify-start overflow-x-auto scrollbar-thin gap-0.5 sm:gap-0 text-xs"
              role="tablist"
              aria-label="AI 分析子页签，可横向滑动"
            >
              {DIALOG_TABS.map(({ value, label, icon: Icon }) => (
                <TabsTrigger key={value} value={value} className="text-xs px-2 sm:px-1 shrink-0 gap-1">
                  <Icon className="h-3.5 w-3.5 sm:hidden" aria-hidden />
                  <span>{label}</span>
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          {/* 内容滚动区：移动端 pb-24 为吸底 Footer 预留空间，避免内容被遮挡 */}
          <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0 mt-4 px-4 sm:px-0 pr-1 pb-24 sm:pb-1 sm:max-h-[calc(90vh-200px)]">
            <TabsContent value="hot_money" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="hot_money_view"
                templateKey="top_speculative_investor_v1"
                promptContent={promptContent}
                promptLoading={promptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="hot_money"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="hot_money_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="hot_money_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『游资』Tab 点击记录旁的复盘按钮触发。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="midline_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="midline_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『中线』Tab 点击记录旁的复盘按钮触发。建议原报告发布 ≥20 天后复盘。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="longterm_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="longterm_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『价值』Tab 点击记录旁的复盘按钮触发。建议原报告发布 ≥90 天后复盘。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="data_collection" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="stock_data_collection"
                promptContent={dataCollectionPrompt}
                promptLoading={dataCollectionPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="midline" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="midline_industry_expert"
                templateKey="midline_industry_expert_v1"
                promptContent={midlinePrompt}
                promptLoading={midlinePromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="midline"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="longterm" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="longterm_value_watcher"
                templateKey="longterm_value_watcher_v1"
                promptContent={longtermPrompt}
                promptLoading={longtermPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="longterm"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="cio" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="cio_directive"
                templateKey="cio_directive_v1"
                promptContent={cioPrompt}
                promptLoading={cioPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>
          </div>
        </Tabs>

        {/* Footer：<sm 吸底（含 iOS safe-area），≥sm 跟随 Radix 默认右对齐 */}
        <DialogFooter
          className="shrink-0 mt-0 sm:mt-4 gap-2 max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-10 max-sm:flex-row max-sm:justify-end max-sm:items-center max-sm:border-t max-sm:border-border max-sm:bg-background/95 max-sm:backdrop-blur max-sm:px-4 max-sm:py-3 max-sm:pb-[calc(env(safe-area-inset-bottom)+0.75rem)]"
        >
          {multiMsg && (
            <p className={`text-xs mr-auto self-center ${multiMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
              {multiMsg.text}
            </p>
          )}
          <Button
            onClick={handleMultiGenerate}
            disabled={multiGenerating}
            size="sm"
            className="gap-1.5"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {multiGenerating ? '分析中...' : '一键分析'}
          </Button>
          <Button variant="outline" size="sm" onClick={onClose}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
