'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
} from 'lucide-react'

// ── 类型 ──────────────────────────────────────────────────────

export interface AnalysisRecord {
  id: number
  ts_code: string
  analysis_type: string
  analysis_text: string
  score: number | null
  prompt_text: string | null
  ai_provider: string | null
  ai_model: string | null
  version: number
  created_at: string
}

export interface HotMoneyViewDialogProps {
  open: boolean
  onClose: () => void
  stockName: string
  stockCode: string   // 纯代码，如 000001
  tsCode: string      // ts_code，如 000001.SZ
  promptContent: string
  promptLoading: boolean
  onSaved?: () => void
}

// ── 组件 ──────────────────────────────────────────────────────

export function HotMoneyViewDialog({
  open, onClose, stockName, stockCode, tsCode, promptContent, promptLoading, onSaved,
}: HotMoneyViewDialogProps) {
  const [copied, setCopied] = useState(false)
  const [promptExpanded, setPromptExpanded] = useState(false)

  const [history, setHistory] = useState<AnalysisRecord[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  const [analysisText, setAnalysisText] = useState('')
  const [scoreInput, setScoreInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 编辑状态
  const [editMode, setEditMode] = useState(false)
  const [editText, setEditText] = useState('')
  const [editScore, setEditScore] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editMsg, setEditMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 删除确认
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const currentRecord: AnalysisRecord | null = history[currentIndex] ?? null

  useEffect(() => {
    if (!open || !tsCode) return
    setHistory([])
    setHistoryTotal(0)
    setCurrentIndex(0)
    setAnalysisText('')
    setScoreInput('')
    setSaveMsg(null)
    setPromptExpanded(false)
    setCopied(false)
    setEditMode(false)
    setDeleteConfirm(false)

    setHistoryLoading(true)
    apiClient.getStockAnalysisHistory(tsCode, 'hot_money_view', 50, 0)
      .then((res) => {
        if (res?.code === 200 && res.data) {
          setHistory(res.data.items ?? [])
          setHistoryTotal(res.data.total ?? 0)
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoading(false))
  }, [open, tsCode])

  // 切换记录时退出编辑模式
  useEffect(() => {
    setEditMode(false)
    setDeleteConfirm(false)
    setEditMsg(null)
  }, [currentIndex])

  const reloadHistory = async () => {
    const histRes = await apiClient.getStockAnalysisHistory(tsCode, 'hot_money_view', 50, 0)
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

  const handleSave = async () => {
    if (!analysisText.trim()) {
      setSaveMsg({ text: '请输入分析内容', type: 'error' })
      return
    }
    const score = scoreInput.trim() ? parseFloat(scoreInput) : undefined
    if (score !== undefined && (isNaN(score) || score < 0 || score > 10)) {
      setSaveMsg({ text: '评分需在 0-10 之间', type: 'error' })
      return
    }
    setSaving(true)
    setSaveMsg(null)
    try {
      const res = await apiClient.saveStockAnalysis({
        ts_code: tsCode,
        analysis_type: 'hot_money_view',
        analysis_text: analysisText.trim(),
        score,
        prompt_text: promptContent || undefined,
      })
      if (res?.code === 201 || res?.code === 200) {
        setSaveMsg({ text: '保存成功', type: 'success' })
        setAnalysisText('')
        setScoreInput('')
        await reloadHistory()
        onSaved?.()
      } else {
        setSaveMsg({ text: res?.message || '保存失败', type: 'error' })
      }
    } catch (e: any) {
      setSaveMsg({ text: e?.response?.data?.message || '保存失败', type: 'error' })
    } finally {
      setSaving(false)
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
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[720px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>游资观点：{stockName}（{stockCode}）</DialogTitle>
          <DialogDescription>保存并回顾每次 AI 游资分析结果</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto min-h-0 space-y-4 pr-1">

          {/* 历史记录区 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                已保存分析
                {historyTotal > 0 && (
                  <span className="ml-1.5 text-xs text-gray-400">（共 {historyTotal} 条）</span>
                )}
              </span>
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
                  <span className="text-xs text-gray-500 min-w-[60px] text-center">
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

            {historyLoading ? (
              <div className="text-center py-6 text-gray-400 text-sm">加载中...</div>
            ) : currentRecord ? (
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
                {/* 记录头部：版本信息 + 操作按钮 */}
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>
                    版本 {currentRecord.version} · {new Date(currentRecord.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <div className="flex items-center gap-2">
                    {currentRecord.score !== null && !editMode && (
                      <span className={`font-semibold px-2 py-0.5 rounded text-sm ${
                        currentRecord.score >= 8 ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                        : currentRecord.score >= 6 ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
                        : 'bg-gray-50 text-gray-500 dark:bg-gray-800'
                      }`}>
                        评分 {currentRecord.score}
                      </span>
                    )}
                    {!editMode && !deleteConfirm && (
                      <>
                        <button
                          onClick={handleEditStart}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-500"
                          title="编辑"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(true)}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-red-500"
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
                      <span className="text-xs text-gray-400">评分（可选）</span>
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
                ) : (
                  <div className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {currentRecord.analysis_text}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6 text-gray-400 text-sm border border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
                暂无保存记录，在下方输入 AI 分析结果后保存
              </div>
            )}
          </div>

          {/* 保存新记录区 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">保存新分析</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">评分（可选）</span>
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  value={scoreInput}
                  onChange={(e) => setScoreInput(e.target.value)}
                  placeholder="0-10"
                  className="w-20 h-7 text-xs border border-gray-200 dark:border-gray-600 rounded px-2 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                />
              </div>
            </div>
            <textarea
              value={analysisText}
              onChange={(e) => setAnalysisText(e.target.value)}
              placeholder="将 AI 返回的游资观点分析粘贴到这里..."
              rows={6}
              className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg p-3 resize-none bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {saveMsg && (
              <p className={`text-xs ${saveMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                {saveMsg.text}
              </p>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !analysisText.trim()}
              size="sm"
              className="gap-1.5"
            >
              <Save className="h-3.5 w-3.5" />
              {saving ? '保存中...' : '保存分析结果'}
            </Button>
          </div>

          {/* 提示词（可折叠） */}
          <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
            <button
              onClick={() => setPromptExpanded((v) => !v)}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              {promptExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              提示词
            </button>
            {promptExpanded && (
              <div className="mt-2">
                {promptLoading ? (
                  <div className="text-center py-4 text-gray-400 text-sm">加载中...</div>
                ) : (
                  <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 leading-relaxed font-mono max-h-60 overflow-y-auto">
                    {promptContent}
                  </pre>
                )}
              </div>
            )}
          </div>

        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>关闭</Button>
          <Button
            variant="outline"
            onClick={handleCopy}
            disabled={promptLoading || !promptContent}
            className="gap-1.5"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? '已复制' : '复制提示词'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
