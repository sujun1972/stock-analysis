// Barrel export for the analysis components shared between
// the in-page expert cards (/analysis) and HotMoneyViewDialog.
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
export { ExpertDetailCard, type ExpertDetailCardProps } from './ExpertDetailCard'
