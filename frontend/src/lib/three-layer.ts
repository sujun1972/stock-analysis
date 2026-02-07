/**
 * 三层架构API导出
 * 统一导出点，方便组件导入
 */

export { threeLayerApi, ThreeLayerApiError } from './three-layer-api'
export type {
  SelectorInfo,
  EntryInfo,
  ExitInfo,
  StrategyConfig,
  BacktestResult,
  BacktestResultData,
  ValidationResult,
  ParameterDef,
  Trade,
  DailyPortfolio,
  ApiResponse,
  ComponentListResponse,
} from './three-layer-types'
