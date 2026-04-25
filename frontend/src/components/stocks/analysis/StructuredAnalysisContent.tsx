'use client'

import React from 'react'
import { renderBold } from './text-utils'
import { MarkdownContent } from './markdown'
import {
  ScoreBadge,
  ProsConsList,
  DimensionSection,
  GenericSection,
  FollowupTriggersSection,
} from './sections'
import {
  SECTION_CONFIGS,
  PM_FIELD_LABELS,
  JSON_ANALYSIS_TYPES,
} from './section-configs'

/**
 * 通用 JSON 结构化分析渲染器。
 * 根据 analysisType 查找 SECTION_CONFIGS，按声明的 section 顺序渲染；
 * 配置外的顶层字段（risk_warning / final_score / followup_triggers）由专门逻辑处理；
 * 兼容旧 schema（probability_metrics / dimensions / trading_strategy / pros/cons）。
 *
 * `hideFinalScore` / `hideTitleHeader`：主页 ExpertDetailCard 已在卡片头部独立渲染评分 +
 * 标题，所以正文里不再重复输出。弹窗内调用时不传这两个 prop（保持原行为）。
 */
export function StructuredAnalysisContent({
  d,
  analysisType,
  hideFinalScore = false,
  hideTitleHeader = false,
}: {
  d: Record<string, any>
  analysisType: string
  hideFinalScore?: boolean
  hideTitleHeader?: boolean
}) {
  const sections = SECTION_CONFIGS[analysisType] ?? []
  const fs = d.final_score as Record<string, any> | undefined
  const score = fs?.score != null ? parseFloat(String(fs.score)) : null

  const bullFactors = Array.isArray(fs?.bull_factors) ? fs.bull_factors : (Array.isArray(fs?.pros) ? fs.pros : [])
  const bearFactors = Array.isArray(fs?.bear_factors) ? fs.bear_factors : (Array.isArray(fs?.cons) ? fs.cons : [])

  const pm = d.probability_metrics as Record<string, any> | undefined
  const ts = d.trading_strategy as Record<string, any> | undefined

  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed space-y-3">
      {!hideTitleHeader && (
        <div className="pb-2 border-b border-gray-100 dark:border-gray-700">
          <p className="font-bold text-base">
            {d.expert_identity ?? '专家'}{d.stock_target ? ` · ${d.stock_target}` : ''}
          </p>
          {d.analysis_date && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{d.analysis_date}</p>
          )}
        </div>
      )}

      {sections.map((cfg) => {
        const sectionData = d[cfg.key]
        if (sectionData == null || sectionData === '') return null

        if (typeof sectionData === 'string') {
          return (
            <section key={cfg.key}>
              <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{cfg.title}</h3>
              <p className="text-sm leading-relaxed">{renderBold(sectionData)}</p>
            </section>
          )
        }

        if (Array.isArray(sectionData)) {
          if (sectionData.length === 0) return null
          return (
            <section key={cfg.key}>
              <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{cfg.title}</h3>
              <ul className="space-y-1.5 pl-1">
                {sectionData.map((item, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-400 dark:text-gray-600 shrink-0">·</span>
                    {typeof item === 'string' ? (
                      <span className="flex-1">{renderBold(item)}</span>
                    ) : item && typeof item === 'object' ? (
                      <div className="flex-1 space-y-0.5">
                        {Object.entries(item).map(([k, v]) => (
                          <div key={k} className="text-xs">
                            <span className="text-gray-500 dark:text-gray-400">{k.replace(/_/g, ' ')}：</span>
                            <span>{renderBold(String(v ?? '-'))}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          )
        }

        if (typeof sectionData === 'object') {
          return <GenericSection key={cfg.key} title={cfg.title} data={sectionData} labels={cfg.labels} />
        }
        return null
      })}

      {pm && Object.keys(pm).length > 0 && !sections.some((cfg) => d[cfg.key]) && (
        <GenericSection
          title="核心指标"
          data={pm}
          labels={Object.fromEntries(
            Object.entries(PM_FIELD_LABELS).map(([k, v]) => [k, v.label]),
          )}
        />
      )}

      {d.dimensions && Object.values(d.dimensions).map((dim: any, i: number) =>
        dim?.title && dim?.content ? (
          <DimensionSection key={i} title={dim.title} content={dim.content} />
        ) : null,
      )}

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

      {typeof d.risk_warning === 'string' && d.risk_warning.trim() && (
        <section>
          <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1">风险提示</h3>
          <p className="text-sm">{renderBold(d.risk_warning)}</p>
        </section>
      )}

      {d.followup_triggers && typeof d.followup_triggers === 'object' && (
        <FollowupTriggersSection triggers={d.followup_triggers as Record<string, any>} />
      )}

      {!hideFinalScore && fs && score != null && (
        <section className="border-t border-gray-100 dark:border-gray-700 pt-3">
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">综合评分</h3>
          <ScoreBadge score={score} rating={fs.rating} />
          {typeof fs.key_quote === 'string' && fs.key_quote.trim() && (
            <p className="mt-2 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-md text-sm font-semibold text-blue-800 dark:text-blue-200">
              {renderBold(fs.key_quote)}
            </p>
          )}
          {bullFactors.length > 0 && (
            <div className="mt-2">
              <span className="font-semibold text-gray-700 dark:text-gray-300">正向因子</span>
              <ProsConsList items={bullFactors} variant="pros" />
            </div>
          )}
          {bearFactors.length > 0 && (
            <div className="mt-1.5">
              <span className="font-semibold text-gray-700 dark:text-gray-300">负向因子</span>
              <ProsConsList items={bearFactors} variant="cons" />
            </div>
          )}
        </section>
      )}
    </div>
  )
}

/**
 * 分析内容渲染入口。JSON 类型走 StructuredAnalysisContent；其他走 MarkdownContent。
 */
export function AnalysisContent({
  text,
  analysisType,
  hideFinalScore,
  hideTitleHeader,
}: {
  text: string
  analysisType: string
  hideFinalScore?: boolean
  hideTitleHeader?: boolean
}) {
  if (JSON_ANALYSIS_TYPES.has(analysisType)) {
    try {
      const d = JSON.parse(text)
      if (d && typeof d === 'object' && !Array.isArray(d)) {
        return (
          <StructuredAnalysisContent
            d={d}
            analysisType={analysisType}
            hideFinalScore={hideFinalScore}
            hideTitleHeader={hideTitleHeader}
          />
        )
      }
    } catch {
      // JSON 解析失败 → 降级为 Markdown
    }
  }
  return <MarkdownContent text={text} />
}
