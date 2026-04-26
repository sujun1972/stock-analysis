'use client'

import React, { useEffect, useState } from 'react'
import { Brain, ChevronDown, ChevronUp } from 'lucide-react'
import { renderBold } from './text-utils'
import { GenericSection, FollowupTriggersSection } from './sections'
import { safeParseJSON, scoreToneClass, extractScore, extractKeyQuote } from './expert-meta'
import { useAnalysisHistory } from './useAnalysisHistory'
import {
  TradeDateVersionPager,
  RecordActionToolbar,
  DeleteConfirmDialog,
  EditAnalysisDialog,
  ViewSourceDialog,
} from './RecordActions'

export interface CioDecisionCardProps {
  /** ts_code drives the in-card history fetch (pager → 1/N versions). */
  tsCode: string
  /** Default open state when component mounts (e.g. radar click sets true). */
  defaultOpen?: boolean
  /** External refresh trigger (one-key analysis, regenerate). */
  refreshKey?: number
  /** Bumped after inline edit/delete so /analysis page can re-fetch latest. */
  onChange?: () => void
  /** Anchor id for scrollIntoView. */
  id?: string
}

/**
 * CIO Comprehensive Decision detail card (card ③).
 *
 * Refactor: history is now resolved in-card (no more `analysisText` prop).
 * Header carries the version pager + edit/delete/source toolbar so traders can
 * flip back through prior CIO directives without leaving the page.
 *
 * No review sub-tab — CIO directives have no review type.
 */
export function CioDecisionCard({
  tsCode,
  defaultOpen = false,
  refreshKey,
  onChange,
  id,
}: CioDecisionCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  // Sync external "should be open" hint (radar click reuses the same instance
  // and bumps key) — without this, a re-click after manual collapse is a no-op.
  useEffect(() => {
    if (defaultOpen) setOpen(true)
  }, [defaultOpen])

  const history = useAnalysisHistory(tsCode, 'cio_directive', refreshKey)

  const [showDelete, setShowDelete] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showSource, setShowSource] = useState(false)

  const current = history.current
  const parsed = safeParseJSON(current?.analysis_text)

  // Render dialogs from a const so both the empty-state branch and the normal
  // branch can mount the same elements without duplicating JSX.
  const dialogs = (
    <>
      <DeleteConfirmDialog
        open={showDelete}
        record={current}
        onClose={() => setShowDelete(false)}
        contextLabel="CIO 综合决策"
        onConfirm={async () => {
          if (!current) return { ok: false, message: '无可删除记录' }
          const r = await history.remove(current.id)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <EditAnalysisDialog
        open={showEdit}
        record={current}
        onClose={() => setShowEdit(false)}
        contextLabel="CIO 综合决策"
        onSave={async (params) => {
          if (!current) return { ok: false, message: '无可编辑记录' }
          const r = await history.update(current.id, params)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <ViewSourceDialog
        open={showSource}
        record={current}
        onClose={() => setShowSource(false)}
        contextLabel="CIO 综合决策"
      />
    </>
  )

  // 两套空态分支：!current 是"真没记录" → "尚未生成"；!parsed 是"有记录但 JSON
  // 解析不出"→"内容解析失败"。后端写库前已强校验合法 JSON，新数据不会再走 !parsed,
  // 但历史 DB 仍有畸形遗留（例如 LLM 偶发输出字符串内未转义引号），保留兜底。
  if (!current) {
    return (
      <section
        id={id}
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card p-3 sm:p-5"
      >
        <header className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-expert-cio" aria-hidden />
          <h2 className="text-base font-semibold">CIO 综合决策</h2>
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            {history.loading ? '加载中…' : '尚未生成'}
          </span>
        </header>
        {dialogs}
      </section>
    )
  }

  if (!parsed) {
    // 给用户三条出路：翻页到其他合法版本 / 查看源代码 / 删除该版本后重新生成
    return (
      <section
        id={id}
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card p-3 sm:p-5"
      >
        <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Brain className="h-5 w-5 text-expert-cio" aria-hidden />
          <h2 className="text-base font-semibold">CIO 综合决策</h2>
          <span className="text-xs text-amber-600 dark:text-amber-400">
            内容解析失败
          </span>
          <div className="ml-auto flex flex-wrap items-center gap-x-2 gap-y-1.5">
            <TradeDateVersionPager
              groups={history.groups}
              selectedTradeDate={history.selectedTradeDate}
              onSelectTradeDate={history.setSelectedTradeDate}
              versions={history.versions}
              versionIndex={history.versionIndex}
              onPrevVersion={history.goOlderVersion}
              onNextVersion={history.goNewerVersion}
              loading={history.loading}
            />
            <RecordActionToolbar
              onView={() => setShowSource(true)}
              onDelete={() => setShowDelete(true)}
            />
          </div>
        </header>
        <p className="mt-3 text-xs text-muted-foreground">
          v{current.displayVersion}/{current.displayTotal} 的 JSON 不合法，无法结构化渲染。
          可翻到其他版本，或点击「源代码」查看 LLM 原始输出，或删除该版本后重新生成。
        </p>
        {dialogs}
      </section>
    )
  }

  const score = extractScore(parsed)
  const keyQuote = extractKeyQuote(parsed)
  const ra = parsed.rating_and_action as Record<string, any> | undefined
  const md = parsed.multi_dimension_scan as Record<string, any> | undefined
  const cd = parsed.cross_dimension_analysis as Record<string, any> | undefined
  const drivers = parsed.core_drivers
  const risks = parsed.core_risks
  const triggers = parsed.followup_triggers as Record<string, any> | undefined

  return (
    <section
      id={id}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card overflow-hidden"
    >
      {/* The toggle is a sibling <button> rather than an outer wrapper so the
          pager and toolbar can receive their own clicks without flicking the
          collapse open. Right group wraps below on <sm via flex-wrap+ml-auto. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 sm:px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 min-w-[200px] items-center gap-3 text-left rounded transition-colors duration-fast hover:bg-gray-50 dark:hover:bg-gray-800/40 -mx-2 px-2 py-1 focus-ring"
          aria-expanded={open}
          aria-controls={id ? `${id}-body` : undefined}
        >
          <Brain className="h-5 w-5 text-expert-cio shrink-0" aria-hidden />
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 flex-wrap">
              <h2 className="text-base font-semibold">CIO 综合决策</h2>
              {score != null && (
                <span className={`text-base font-bold tabular-nums ${scoreToneClass(score)}`}>
                  {Number.isInteger(score) ? score.toFixed(1) : score}
                </span>
              )}
              {ra?.rating && (
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {String(ra.rating)}
                </span>
              )}
            </div>
            {keyQuote && !open && (
              <p
                className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-1"
                title={keyQuote}
              >
                "{keyQuote}"
              </p>
            )}
          </div>
          {open ? (
            <ChevronUp className="h-4 w-4 text-gray-400" aria-hidden />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden />
          )}
        </button>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 shrink-0 ml-auto">
          <TradeDateVersionPager
            groups={history.groups}
            selectedTradeDate={history.selectedTradeDate}
            onSelectTradeDate={history.setSelectedTradeDate}
            versions={history.versions}
            versionIndex={history.versionIndex}
            onPrevVersion={history.goOlderVersion}
            onNextVersion={history.goNewerVersion}
            loading={history.loading}
          />
          <RecordActionToolbar
            onView={() => setShowSource(true)}
            onEdit={() => setShowEdit(true)}
            onDelete={() => setShowDelete(true)}
          />
        </div>
      </div>

      {open && (
        <div
          id={id ? `${id}-body` : undefined}
          className="border-t border-gray-100 dark:border-gray-800 p-3 sm:p-5 space-y-4 sm:space-y-5"
        >
          {keyQuote && (
            <p className="px-3 py-2 rounded bg-expert-cio/10 dark:bg-expert-cio/20 text-sm font-medium text-expert-cio dark:text-expert-cio">
              {renderBold(keyQuote)}
            </p>
          )}

          {md && <MultiDimensionScan data={md} />}

          {cd && Object.keys(cd).length > 0 && (
            <GenericSection
              title="跨维度共振/矛盾"
              data={cd}
              labels={{
                consensus_or_conflict: '方向一致性',
                conflict_essence: '矛盾本质',
                cio_resolution: 'CIO 取舍',
              }}
            />
          )}

          <DriversRisksGrid drivers={drivers} risks={risks} />

          {ra && <RatingActionCard data={ra} />}

          {triggers && <FollowupTriggersSection triggers={triggers} />}
        </div>
      )}

      {dialogs}
    </section>
  )
}

function MultiDimensionScan({ data }: { data: Record<string, any> }) {
  const dims: { key: string; title: string }[] = [
    { key: 'short_term', title: '短线（1-5 日）' },
    { key: 'mid_term', title: '中线（1-3 月）' },
    { key: 'long_term', title: '长线（1-3 年）' },
  ]
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">
        多维度快速扫描
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {dims.map(({ key, title }) => {
          const v = data[key]
          if (v == null) return null
          if (typeof v === 'string') {
            return (
              <div
                key={key}
                className="rounded border border-gray-200 dark:border-gray-700 p-3 bg-background"
              >
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">
                  {title}
                </div>
                <p className="text-sm">{renderBold(v)}</p>
              </div>
            )
          }
          const entries = Object.entries(v).filter(([, val]) => val != null && val !== '')
          return (
            <div
              key={key}
              className="rounded border border-gray-200 dark:border-gray-700 p-3 bg-background"
            >
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">
                {title}
              </div>
              <ul className="text-xs space-y-1">
                {entries.map(([k, val]) => (
                  <li key={k}>
                    <span className="text-gray-500 dark:text-gray-400">
                      {k.replace(/_/g, ' ')}：
                    </span>
                    <span>{renderBold(String(val ?? '-'))}</span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function DriversRisksGrid({ drivers, risks }: { drivers: any; risks: any }) {
  type Item = { name?: string; description?: string; raw?: string }
  const toList = (v: any): Item[] => {
    if (Array.isArray(v)) {
      return v
        .map((x) => {
          if (typeof x === 'string') return { raw: x }
          if (x && typeof x === 'object') {
            const name = x.name ?? x.factor ?? x.title
            const description = x.description ?? x.desc ?? x.reason ?? x.evidence
            if (name || description) return { name, description }
            const firstVal = Object.values(x).find((vv) => vv != null && vv !== '')
            return { raw: firstVal != null ? String(firstVal) : '' }
          }
          return { raw: String(x ?? '') }
        })
        .filter((it) => it.name || it.description || it.raw)
    }
    if (typeof v === 'string' && v.trim()) {
      return v
        .split('\n')
        .filter((s) => s.trim())
        .map((raw) => ({ raw }))
    }
    return []
  }
  const dList = toList(drivers)
  const rList = toList(risks)
  if (dList.length === 0 && rList.length === 0) return null

  const renderItem = (item: Item, idx: number, sign: '+' | '−') => {
    const signCls = sign === '+' ? 'text-emerald-500' : 'text-red-400'
    return (
      <li key={idx} className="flex gap-1.5">
        <span className={`shrink-0 ${signCls}`} aria-hidden>
          {sign}
        </span>
        <span className="flex-1">
          {item.name && (
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {renderBold(item.name)}
            </span>
          )}
          {item.name && item.description && (
            <span className="text-gray-500 dark:text-gray-400">：</span>
          )}
          {item.description && (
            <span className="text-gray-700 dark:text-gray-300">
              {renderBold(item.description)}
            </span>
          )}
          {item.raw && !item.name && !item.description && <span>{renderBold(item.raw)}</span>}
        </span>
      </li>
    )
  }

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <h3 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1.5 flex items-center gap-1.5">
          <span aria-hidden>▲</span>核心驱动因子
        </h3>
        {dList.length > 0 ? (
          <ul className="space-y-1 pl-1">{dList.map((it, i) => renderItem(it, i, '+'))}</ul>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500">—</p>
        )}
      </div>
      <div>
        <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1.5 flex items-center gap-1.5">
          <span aria-hidden>▼</span>核心风险因子
        </h3>
        {rList.length > 0 ? (
          <ul className="space-y-1 pl-1">{rList.map((it, i) => renderItem(it, i, '−'))}</ul>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500">—</p>
        )}
      </div>
    </section>
  )
}

function RatingActionCard({ data }: { data: Record<string, any> }) {
  const action = String(data.action ?? '')
  const tone = /加仓|买入|看多|建仓|逢低/i.test(action)
    ? 'positive'
    : /减仓|禁飞|看空|卖出|清仓|警惕/i.test(action)
    ? 'negative'
    : 'neutral'
  const toneCls =
    tone === 'positive'
      ? 'border-positive/40 bg-positive-soft text-positive'
      : tone === 'negative'
      ? 'border-negative/40 bg-negative-soft text-negative'
      : 'border-gray-200 dark:border-gray-700 bg-muted text-foreground'

  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">
        综合评级与行动指令
      </h3>
      <div className={`rounded-lg border p-4 ${toneCls}`}>
        <div className="flex flex-wrap items-baseline gap-3 mb-1">
          {data.rating && <span className="text-base font-bold">{String(data.rating)}</span>}
          {data.action && <span className="text-sm font-medium">{String(data.action)}</span>}
        </div>
        {data.price_reference && (
          <div className="text-xs mt-2 opacity-90">
            <span className="font-semibold">价位区间参考：</span>
            <span className="tabular-nums">{String(data.price_reference)}</span>
          </div>
        )}
        {data.rating_logic && (
          <p className="text-xs mt-2 opacity-90 leading-relaxed">
            {renderBold(String(data.rating_logic))}
          </p>
        )}
      </div>
    </section>
  )
}
