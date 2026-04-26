// Barrel export for the in-page expert cards on /analysis.
export { renderBold, highlightTags } from './text-utils'
export { markdownComponents, MarkdownContent } from './markdown'
export {
  ScoreBadge,
  ProsConsList,
  DimensionSection,
  FieldValue,
  GenericSection,
  FollowupTriggersSection,
} from './sections'
export {
  StructuredAnalysisContent,
  AnalysisContent,
} from './StructuredAnalysisContent'
export {
  SECTION_CONFIGS,
  PM_FIELD_LABELS,
  JSON_ANALYSIS_TYPES,
  type SectionConfig,
} from './section-configs'

export {
  EXPERTS,
  EXPERT_BY_KEY,
  EXPERT_BY_ANALYSIS_TYPE,
  scoreToneClass,
  safeParseJSON,
  extractScore,
  extractKeyQuote,
  extractRating,
  extractBullBearCount,
  type ExpertMeta,
} from './expert-meta'

export { ExpertSummaryCard, type LatestAnalysisRecord, type ExpertSummaryCardProps } from './ExpertSummaryCard'
export { CioDecisionCard, type CioDecisionCardProps } from './CioDecisionCard'
export { DataCollectionCard, type DataCollectionCardProps } from './DataCollectionCard'
export { ExpertDetailCard, type ExpertDetailCardProps } from './ExpertDetailCard'
export { useAnalysisHistory, type UseAnalysisHistoryResult } from './useAnalysisHistory'
export {
  TradeDateVersionPager,
  RecordActionToolbar,
  DeleteConfirmDialog,
  EditAnalysisDialog,
  ViewSourceDialog,
} from './RecordActions'
export {
  groupRecordsByTradeDate,
  normalizeTradeDate,
  parseTradeDateToDate,
  formatDateToTradeDate,
  type TradeDateGroup,
} from './trade-date-utils'
