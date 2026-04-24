'use client'

import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'

interface ErrorDetailCollapsibleProps {
  /** 顶部标题（如"验证错误"） */
  title: string
  /** 任意 JSON 可序列化错误对象：字符串 / 数组 / 对象均可 */
  errors: unknown
  /** 折叠时展示的一行摘要（可选，缺省自动生成） */
  summary?: string
  className?: string
}

/** 从错误对象提取一行人类可读摘要；按"最可能是错误消息"的字段顺序探测 */
function formatSummary(errors: unknown): string {
  if (errors == null) return ''
  if (typeof errors === 'string') return errors

  const extractMessage = (obj: Record<string, unknown>): string | null => {
    const msg = obj.message ?? obj.error ?? obj.detail
    return typeof msg === 'string' ? msg : null
  }

  if (Array.isArray(errors)) {
    const suffix = errors.length > 1 ? ` · 等 ${errors.length} 条` : ''
    const first = errors[0]
    if (typeof first === 'string') return first + suffix
    if (first && typeof first === 'object') {
      const msg = extractMessage(first as Record<string, unknown>)
      if (msg) return msg + suffix
    }
    return `${errors.length} 条错误`
  }

  if (typeof errors === 'object') {
    const obj = errors as Record<string, unknown>
    const msg = extractMessage(obj)
    if (msg) return msg
    return `${Object.keys(obj).length} 个字段错误`
  }

  return String(errors)
}

/** 结构化展开错误：字符串 → pre / 数组 → 有序列表 / 对象 → 键值对 dl */
function renderStructured(errors: unknown): React.ReactNode {
  if (errors == null) return null

  if (typeof errors === 'string') {
    return <pre className="text-xs whitespace-pre-wrap break-words">{errors}</pre>
  }

  if (Array.isArray(errors)) {
    return (
      <ul className="space-y-1 text-xs">
        {errors.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-destructive/60 tabular-nums shrink-0">{i + 1}.</span>
            <span className="min-w-0 break-words">
              {typeof item === 'string'
                ? item
                : <code className="font-mono">{JSON.stringify(item, null, 2)}</code>}
            </span>
          </li>
        ))}
      </ul>
    )
  }

  if (typeof errors === 'object') {
    return (
      <dl className="space-y-1 text-xs">
        {Object.entries(errors as Record<string, unknown>).map(([key, value]) => (
          <div key={key} className="flex gap-2">
            <dt className="font-mono text-destructive/80 shrink-0">{key}:</dt>
            <dd className="min-w-0 break-words">
              {typeof value === 'string'
                ? value
                : <code className="font-mono">{JSON.stringify(value)}</code>}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  return <pre className="text-xs">{String(errors)}</pre>
}

/**
 * 可折叠的结构化错误详情卡片。
 * 取代 `<p>{JSON.stringify(errors)}</p>` 这种原样展示——用户看不懂、撑爆容器、无法复制。
 * - 外层 header 只有折叠/展开一个交互，复制按钮独立于 header（避免嵌套 interactive 元素的 a11y 问题）
 * - 复制后 1.5s 自动复位 icon
 */
export function ErrorDetailCollapsible({
  title,
  errors,
  summary,
  className = '',
}: ErrorDetailCollapsibleProps) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const line = summary ?? formatSummary(errors)

  const handleCopy = async () => {
    try {
      const text = typeof errors === 'string' ? errors : JSON.stringify(errors, null, 2)
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // 浏览器拒绝或不支持 clipboard API 时静默降级——错误已经在页面上显示，复制只是便利
    }
  }

  return (
    <div className={`bg-destructive/10 border border-destructive/30 rounded-lg overflow-hidden ${className}`}>
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          aria-expanded={open}
          className="flex items-center gap-2 flex-1 min-w-0 text-left focus-ring-red rounded-sm"
        >
          <span className="text-xs font-medium text-destructive shrink-0">{title}</span>
          <span className="text-xs text-destructive/80 truncate flex-1 min-w-0">{line}</span>
          {open
            ? <ChevronUp className="h-3 w-3 text-destructive shrink-0" aria-hidden />
            : <ChevronDown className="h-3 w-3 text-destructive shrink-0" aria-hidden />}
        </button>
        <button
          type="button"
          onClick={handleCopy}
          aria-label="复制错误详情"
          className="shrink-0 p-1 rounded hover:bg-destructive/20 text-destructive focus-ring-red"
        >
          {copied ? <Check className="h-3 w-3" aria-hidden /> : <Copy className="h-3 w-3" aria-hidden />}
        </button>
      </div>
      {open && (
        <div className="px-3 py-2 border-t border-destructive/30 text-destructive/90 bg-background/40">
          {renderStructured(errors)}
        </div>
      )}
    </div>
  )
}
