'use client'

import React, { useEffect, useState } from 'react'
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

// ── 分析内容渲染 ──────────────────────────────────────────────

/** 将 **加粗** 标记拆分为带 <strong> 的 React 节点数组，避免 dangerouslySetInnerHTML */
function renderBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
  )
}

/**
 * 通用 Markdown 渲染器（轻量级，无外部依赖）。
 * 支持：## 标题、### 标题、**加粗**、- 列表、【标签】高亮、---分隔线、普通段落。
 */
function MarkdownContent({ text }: { text: string }) {
  const lines = text.split('\n')
  const nodes: React.ReactNode[] = []
  let listBuffer: string[] = []

  const flushList = (key: string) => {
    if (listBuffer.length === 0) return
    nodes.push(
      <ul key={key} className="space-y-0.5 pl-1 mb-1">
        {listBuffer.map((item, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-gray-400 shrink-0">·</span>
            <span>{renderBold(item)}</span>
          </li>
        ))}
      </ul>
    )
    listBuffer = []
  }

  lines.forEach((line, idx) => {
    const trimmed = line.trim()

    if (trimmed.startsWith('## ')) {
      flushList(`list-${idx}`)
      nodes.push(
        <h2 key={idx} className="text-base font-bold mt-3 mb-1 text-gray-900 dark:text-gray-100">
          {renderBold(trimmed.slice(3))}
        </h2>
      )
    } else if (trimmed.startsWith('### ')) {
      flushList(`list-${idx}`)
      nodes.push(
        <h3 key={idx} className="text-sm font-semibold text-blue-700 dark:text-blue-400 mt-2 mb-1">
          {renderBold(trimmed.slice(4))}
        </h3>
      )
    } else if (trimmed === '---' || trimmed === '***') {
      flushList(`list-${idx}`)
      nodes.push(<hr key={idx} className="border-gray-200 dark:border-gray-700 my-2" />)
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listBuffer.push(trimmed.slice(2))
    } else if (trimmed === '') {
      flushList(`list-${idx}`)
      // 空行不输出节点
    } else {
      flushList(`list-${idx}`)
      // 普通段落：高亮【标签】
      const parts = trimmed.split(/(【[^】]+】)/g)
      nodes.push(
        <p key={idx} className="mb-1">
          {parts.map((part, i) =>
            /^【[^】]+】$/.test(part)
              ? <span key={i} className="font-semibold text-blue-700 dark:text-blue-400">{part}</span>
              : renderBold(part)
          )}
        </p>
      )
    }
  })
  flushList('list-end')

  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
      {nodes}
    </div>
  )
}

// ── probability_metrics 字段的中文标签映射 ──────────────────────
// key: JSON 字段名 → label: 中文标签，valuePrefix/valueSuffix 包裹值
const PM_FIELD_LABELS: Record<string, { label: string; prefix?: string }> = {
  // 游资观点
  next_day_plus_2_percent_prob: { label: '次日 +2% 概率' },
  confidence_level:             { label: '置信度' },
  key_observation_window:       { label: '观察窗口' },
  // 中线专家
  three_month_positive_return_prob: { label: '3 个月正收益概率' },
  trend_stage:                  { label: '趋势阶段' },
  key_catalyst:                 { label: '核心催化' },
  // 长线价值守望者
  one_year_intrinsic_return_prob:   { label: '1 年内在回报概率' },
  valuation_level:              { label: '估值水位' },
  safety_margin:                { label: '安全边际' },
  // CIO 指令
  short_term_signal:            { label: '短线信号' },
  mid_term_signal:              { label: '中线信号' },
  long_term_signal:             { label: '长线信号' },
}

// ── 共用子组件 ────────────────────────────────────────────────

/** 评分色块 */
function ScoreBadge({ score, rating }: { score: number; rating?: string }) {
  const colorCls = score >= 8
    ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
    : score >= 6
    ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
    : 'bg-gray-50 text-gray-500 dark:bg-gray-800'
  return (
    <span className="flex items-center gap-2 flex-wrap">
      <span className={`font-bold px-2 py-0.5 rounded text-base ${colorCls}`}>
        {score} / 10
      </span>
      {rating && <span className="text-sm text-gray-600 dark:text-gray-300">{rating}</span>}
    </span>
  )
}

/** 带 +/− 前缀的列表（优势/劣势） */
function ProsConsList({ items, variant }: { items: string[]; variant: 'pros' | 'cons' }) {
  if (!items.length) return null
  const icon = variant === 'pros'
    ? <span className="text-green-500 shrink-0">+</span>
    : <span className="text-red-400 shrink-0">−</span>
  return (
    <ul className="mt-0.5 space-y-0.5 pl-1">
      {items.map((item, i) => (
        <li key={i} className="flex gap-1.5">{icon}<span>{renderBold(item)}</span></li>
      ))}
    </ul>
  )
}

/** 一个分析维度节（蓝色标题 + 正文） */
function DimensionSection({ title, content }: { title: string; content: string }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{title}</h3>
      <div className="text-sm leading-relaxed">
        {content.split('\n').map((line, i) => (
          line.trim() ? <p key={i} className="mb-0.5">{renderBold(line)}</p> : null
        ))}
      </div>
    </section>
  )
}

/**
 * 通用 JSON 结构化分析渲染器。
 * 支持：游资观点 / 中线专家 / 长线价值守望者 / CIO 指令，
 * 所有类型共用同一套骨架渲染逻辑，仅 probability_metrics 字段名通过映射表转换。
 */
function StructuredAnalysisContent({ d }: { d: Record<string, any> }) {
  const pm  = d.probability_metrics as Record<string, any> | undefined
  const ts  = d.trading_strategy    as Record<string, any> | undefined
  const fs  = d.final_score         as Record<string, any> | undefined
  const score = fs?.score != null ? parseFloat(String(fs.score)) : null

  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed space-y-3">

      {/* 标题行：专家身份 · 标的 · 日期 */}
      <div className="pb-2 border-b border-gray-100 dark:border-gray-700">
        <p className="font-bold text-base">
          {d.expert_identity ?? '专家'}{d.stock_target ? ` · ${d.stock_target}` : ''}
        </p>
        {d.analysis_date && (
          <p className="text-xs text-gray-400 mt-0.5">{d.analysis_date}</p>
        )}
      </div>

      {/* 概率指标区 */}
      {pm && Object.keys(pm).length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">核心指标</h3>
          <ul className="space-y-0.5 pl-1">
            {Object.entries(pm).map(([key, val], i) => {
              const meta = PM_FIELD_LABELS[key]
              const label = meta?.label ?? key.replace(/_/g, ' ')
              return (
                <li key={i} className="flex gap-1.5">
                  <span className="text-gray-400 shrink-0">·</span>
                  <span>
                    <span className="text-gray-500 dark:text-gray-400">{label}：</span>
                    <strong>{renderBold(String(val ?? '-'))}</strong>
                  </span>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {/* 维度分析（title + content 结构） */}
      {d.dimensions && Object.values(d.dimensions).map((dim: any, i: number) =>
        dim?.title && dim?.content
          ? <DimensionSection key={i} title={dim.title} content={dim.content} />
          : null
      )}

      {/* 交易策略（游资观点专属，其他类型若有则展示） */}
      {ts && (ts.action_plan || ts.risk_warning) && (
        <section>
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">交易策略</h3>
          {ts.action_plan && (
            <div className="mb-1">
              <span className="font-semibold text-gray-700 dark:text-gray-300">操作方案　</span>
              <span>{renderBold(ts.action_plan)}</span>
            </div>
          )}
          {ts.risk_warning && (
            <div>
              <span className="font-semibold text-gray-700 dark:text-gray-300">风险提示　</span>
              <span>{renderBold(ts.risk_warning)}</span>
            </div>
          )}
        </section>
      )}

      {/* 综合评分区 */}
      {fs && score != null && (
        <section className="border-t border-gray-100 dark:border-gray-700 pt-3">
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">综合评分</h3>
          <ScoreBadge score={score} rating={fs.rating} />
          {Array.isArray(fs.pros) && fs.pros.length > 0 && (
            <div className="mt-2">
              <span className="font-semibold text-gray-700 dark:text-gray-300">优势</span>
              <ProsConsList items={fs.pros} variant="pros" />
            </div>
          )}
          {Array.isArray(fs.cons) && fs.cons.length > 0 && (
            <div className="mt-1.5">
              <span className="font-semibold text-gray-700 dark:text-gray-300">劣势</span>
              <ProsConsList items={fs.cons} variant="cons" />
            </div>
          )}
        </section>
      )}
    </div>
  )
}

/**
 * 分析内容渲染入口。
 * 优先级：结构化 JSON 渲染 → Markdown 渲染 → 纯文本兜底
 */
const JSON_ANALYSIS_TYPES = new Set([
  'hot_money_view', 'midline_industry_expert', 'longterm_value_watcher', 'cio_directive',
])

function AnalysisContent({ text, analysisType }: { text: string; analysisType: string }) {
  if (JSON_ANALYSIS_TYPES.has(analysisType)) {
    try {
      const d = JSON.parse(text)
      if (d && typeof d === 'object' && !Array.isArray(d)) {
        return <StructuredAnalysisContent d={d} />
      }
    } catch {
      // JSON 解析失败，降级
    }
  }

  // Markdown 渲染（文本包含 # 或 - 等 Markdown 特征时更美观）
  if (/^#{1,3} /m.test(text) || /^[-*] /m.test(text)) {
    return <MarkdownContent text={text} />
  }

  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
      {text}
    </div>
  )
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
  onSaved?: () => void
}

function AnalysisTab({
  tsCode, stockName, stockCode, analysisType, templateKey, promptContent, promptLoading, open, onSaved,
}: AnalysisTabProps) {
  const [copied, setCopied] = useState(false)
  const [promptExpanded, setPromptExpanded] = useState(false)

  const [history, setHistory] = useState<AnalysisRecord[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

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
  }, [open, tsCode, analysisType])

  // 切换记录时退出编辑模式
  useEffect(() => {
    setEditMode(false)
    setDeleteConfirm(false)
    setEditMsg(null)
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
              <span className="ml-1.5 text-xs text-gray-400">（共 {historyTotal} 条）</span>
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
              <AnalysisContent text={currentRecord.analysis_text} analysisType={analysisType} />
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-400 text-sm border border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
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
  )
}

// ── 主弹窗组件 ──────────────────────────────────────────────────

export function HotMoneyViewDialog({
  open, onClose, stockName, stockCode, tsCode,
  promptContent, promptLoading,
  dataCollectionPrompt, dataCollectionPromptLoading,
  midlinePrompt, midlinePromptLoading,
  longtermPrompt, longtermPromptLoading,
  cioPrompt, cioPromptLoading,
  onSaved,
}: HotMoneyViewDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[720px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>AI 分析：{stockName}（{stockCode}）</DialogTitle>
          <DialogDescription>保存并回顾每次 AI 分析结果</DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="hot_money" className="flex-1 flex flex-col min-h-0">
          <TabsList className="shrink-0 w-full grid grid-cols-5">
            <TabsTrigger value="hot_money">游资观点</TabsTrigger>
            <TabsTrigger value="data_collection">数据收集</TabsTrigger>
            <TabsTrigger value="midline">中线专家</TabsTrigger>
            <TabsTrigger value="longterm">价值守望</TabsTrigger>
            <TabsTrigger value="cio">CIO 指令</TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto min-h-0 mt-4 pr-1">
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
                onSaved={onSaved}
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
                onSaved={onSaved}
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
                onSaved={onSaved}
              />
            </TabsContent>
          </div>
        </Tabs>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
