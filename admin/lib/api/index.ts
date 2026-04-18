/**
 * @file lib/api/index.ts
 * @description API 客户端统一导出（模块化架构）
 *
 * 所有 API 调用统一从此文件导入：
 *   import { stockApi, syncApi, axiosInstance } from '@/lib/api'
 *
 * - 各模块 API（如 stockApi）提供类型安全的方法
 * - axiosInstance 用于尚无模块覆盖的端点（通用 get/post）
 */

import { BaseApiClient, axiosInstance as axiosInst, API_BASE_URL } from './base'
import { AuthApiClient, authApi as authApiInst } from './auth'
import { StockApiClient, stockApi as stockApiInst } from './stocks'
import { StrategyApiClient, strategyApi as strategyApiInst } from './strategies'
import { UserApiClient, userApi as userApiInst } from './users'
import { SentimentApiClient, sentimentApi as sentimentApiInst } from './sentiment'
import { MoneyflowApiClient, moneyflowApi as moneyflowApiInst } from './moneyflow'
import { HsgtTop10ApiClient, hsgtTop10Api as hsgtTop10ApiInst } from './hsgt-top10'
import { GgtTop10ApiClient, ggtTop10Api as ggtTop10ApiInst } from './ggt-top10'
import { GgtDailyApiClient, ggtDailyApi as ggtDailyApiInst } from './ggt-daily'
import { GgtMonthlyApiClient, ggtMonthlyApi as ggtMonthlyApiInst } from './ggt-monthly'
import { MarginApiClient, marginApi as marginApiInst } from './margin'
import { MarginSecsApi, marginSecsApi as marginSecsApiInst } from './margin-secs'
import { SlbLenApiClient, slbLenApi as slbLenApiInst } from './slb-len'
import { SchedulerApiClient, schedulerApi as schedulerApiInst } from './scheduler'
import { CeleryTasksApiClient, celeryTasksApi as celeryTasksApiInst } from './celery-tasks'
import { ConfigApiClient, configApi as configApiInst } from './config'
import { SyncApiClient, syncApi as syncApiInst } from './sync'
import { ExtendedDataApiClient, extendedDataApi as extendedDataApiInst } from './extended-data'
import { MonitorApiClient, monitorApi as monitorApiInst } from './monitor'
import { TopListApiClient, topListApi as topListApiInst } from './top-list'
import { TopInstApiClient, topInstApi as topInstApiInst } from './top-inst'
import { LimitListApiClient, limitListApi as limitListApiInst } from './limit-list'
import { LimitStepApiClient, limitStepApi as limitStepApiInst } from './limit-step'
import { LimitCptApiClient, limitCptApi as limitCptApiInst } from './limit-cpt'
import { ReportRcApiClient, reportRcApi as reportRcApiInst } from './report-rc'
import { CyqPerfApiClient, cyqPerfApi as cyqPerfApiInst } from './cyq-perf-api'
import { CyqChipsApiClient, cyqChipsApi as cyqChipsApiInst } from './cyq-chips-api'
import { CcassHoldApiClient, ccassHoldApi as ccassHoldApiInst } from './ccass-hold-api'
import { CcassHoldDetailApiClient, ccassHoldDetailApi as ccassHoldDetailApiInst } from './ccass-hold-detail-api'
import { DcMemberApiClient, dcMemberApi as dcMemberApiInst } from './dc-member-api'
import { DcIndexApiClient, dcIndexApi as dcIndexApiInst } from './dc-index-api'
import { DcDailyApiClient, dcDailyApi as dcDailyApiInst } from './dc-daily-api'
import { HkHoldApiClient, hkHoldApi as hkHoldApiInst } from './hk-hold-api'
import { StkAuctionOApiClient, stkAuctionOApi as stkAuctionOApiInst } from './stk-auction-o'
import { StkAuctionCApiClient, stkAuctionCApi as stkAuctionCApiInst } from './stk-auction-c'
import { StkNineturnApiClient, stkNineturnApi as stkNineturnApiInst } from './stk-nineturn-api'
import { StkAhComparisonApiClient, stkAhComparisonApi as stkAhComparisonApiInst } from './stk-ah-comparison'
import { StkSurvApiClient, stkSurvApi as stkSurvApiInst } from './stk-surv-api'
import { StkShockApiClient, stkShockApi as stkShockApiInst } from './stk-shock'
import { StkAlertApiClient, stkAlertApi as stkAlertApiInst } from './stk-alert'
import { StkHighShockApiClient, stkHighShockApi as stkHighShockApiInst } from './stk-high-shock'
import { RepurchaseApiClient, repurchaseApi as repurchaseApiInst } from './repurchase'
import { ShareFloatApiClient, shareFloatApi as shareFloatApiInst } from './share-float'
import { StkHolderNumberApiClient, stkHolderNumberApi as stkHolderNumberApiInst } from './stk-holdernumber'
import { ForecastApiClient, forecastApi as forecastApiInst } from './forecast'
import { BlockTradeApiClient, blockTradeApi as blockTradeApiInst } from './block-trade'
import { StkHoldertradeApiClient, stkHoldertradeApi as stkHoldertradeApiInst } from './stk-holdertrade-api'
import { IncomeApiClient, incomeApi as incomeApiInst } from './income-api'
import { BalancesheetApiClient, balancesheetApi as balancesheetApiInst } from './balancesheet-api'
import { CashflowApiClient, cashflowApi as cashflowApiInst } from './cashflow-api'
import { ExpressApiClient, expressApi as expressApiInst } from './express'
import { FinancialDataApiClient, financialDataApi as financialDataApiInst } from './financial-data'
import { SuspendApiClient, suspendApi as suspendApiInst } from './suspend'
import { StkLimitDApiClient, stkLimitDApi as stkLimitDApiInst } from './stk-limit-d'
import { AdjFactorApiClient, adjFactorApi as adjFactorApiInst } from './adj-factor-api'
import { NewStockApiClient, newStockApi as newStockApiInst } from './new-stock-api'
import { StockDailyApiClient, stockDailyApi as stockDailyApiInst } from './stock-daily'
import { StockListApiClient, stockListApi as stockListApiInst } from './stock-list-api'
import { StockStApiClient, stockStApi as stockStApiInst } from './stock-st-api'
import { TradeCalApiClient, tradeCalApi as tradeCalApiInst } from './trade-cal-api'
import { SyncDashboardApiClient, syncDashboardApi as syncDashboardApiInst } from './sync-dashboard'
import { StockAiAnalysisApiClient, stockAiAnalysisApi as stockAiAnalysisApiInst } from './stock-ai-analysis'
import { DataOpsApiClient, dataOpsApi as dataOpsApiInst } from './data-ops'

// 重新导出基础类和实例
export { BaseApiClient, API_BASE_URL }
export const axiosInstance = axiosInst

// 重新导出认证 API
export { AuthApiClient }
export const authApi = authApiInst
export type { LoginRequest, LoginResponse, RegisterRequest, UpdatePasswordRequest, UpdateProfileRequest } from './auth'

// 重新导出股票 API
export { StockApiClient }
export const stockApi = stockApiInst
export type { StockListParams, UpdateStockRequest } from './stocks'

// 重新导出策略 API
export { StrategyApiClient }
export const strategyApi = strategyApiInst
export type { StrategyListParams, AssignStrategyRequest } from './strategies'

// 重新导出用户 API
export { UserApiClient }
export const userApi = userApiInst
export type {
  User,
  UserListParams,
  CreateUserRequest,
  UpdateUserRequest,
  UserStatistics,
  UserQuota
} from './users'

// 重新导出市场情绪 API
export { SentimentApiClient }
export const sentimentApi = sentimentApiInst
export type { SyncSentimentBatchParams, TradingCalendarParams } from './sentiment'

// 重新导出资金流向 API
export { MoneyflowApiClient }
export const moneyflowApi = moneyflowApiInst

// 重新导出沪深股通十大成交股 API
export { HsgtTop10ApiClient }
export const hsgtTop10Api = hsgtTop10ApiInst
export type { HsgtTop10Data, HsgtTop10Params, HsgtTop10Statistics } from './hsgt-top10'

// 重新导出港股通十大成交股 API
export { GgtTop10ApiClient }
export const ggtTop10Api = ggtTop10ApiInst
export type { GgtTop10Data, GgtTop10Params, GgtTop10Statistics } from './ggt-top10'

// 重新导出港股通每日成交统计 API
export { GgtDailyApiClient }
export const ggtDailyApi = ggtDailyApiInst
export type { GgtDailyData, GgtDailyParams, GgtDailyStatistics } from './ggt-daily'

// 重新导出港股通每月成交统计 API
export { GgtMonthlyApiClient }
export const ggtMonthlyApi = ggtMonthlyApiInst
export type { GgtMonthlyData, GgtMonthlyParams, GgtMonthlyStatistics } from './ggt-monthly'

export type {
  SyncMoneyflowParams,
  SyncTaskResponse,
  MoneyflowHsgtParams,
  MoneyflowMktDcParams,
  MoneyflowIndDcParams,
  MoneyflowStockDcParams,
  MoneyflowParams,
  TopMoneyflowParams
} from './moneyflow'

// 重新导出融资融券 API
export { MarginApiClient }
export const marginApi = marginApiInst
export type {
  MarginParams,
  MarginStatistics,
  SyncMarginParams,
  MarginDetailParams,
  MarginDetailStatistics,
  MarginDetailTopParams
} from './margin'

// 重新导出融资融券标的 API
export { MarginSecsApi }
export const marginSecsApi = marginSecsApiInst
export type {
  MarginSecsParams,
  MarginSecsItem,
  MarginSecsStatistics,
  MarginSecsData,
  LatestMarginSecsData,
} from './margin-secs'

// 重新导出转融资交易汇总 API
export { SlbLenApiClient }
export const slbLenApi = slbLenApiInst
export type {
  SlbLenParams,
  SlbLenData,
  SlbLenStatistics,
  SyncSlbLenParams
} from './slb-len'

// 重新导出定时任务 API
export { SchedulerApiClient }
export const schedulerApi = schedulerApiInst
export type {
  CreateScheduledTaskRequest,
  UpdateScheduledTaskRequest,
  TaskExecutionStatusResponse,
  TaskExecutionResult
} from './scheduler'

// 重新导出 Celery 任务 API
export { CeleryTasksApiClient }
export const celeryTasksApi = celeryTasksApiInst
export type { CeleryTaskParams, CeleryTask } from './celery-tasks'

// 重新导出系统配置 API
export { ConfigApiClient }
export const configApi = configApiInst
export type {
  DataSourceConfig,
  UpdateDataSourceConfigRequest,
  AIProviderConfig
} from './config'

// 重新导出数据同步 API
export { SyncApiClient }
export const syncApi = syncApiInst
export type {
  SyncStatusResponse,
  BatchSyncParams,
  ModuleSyncStatusResponse
} from './sync'

// 重新导出扩展数据 API
export { ExtendedDataApiClient }
export const extendedDataApi = extendedDataApiInst
export type {
  DateRangeParams,
  DailyBasicParams,
  HkHoldParams,
  LimitPricesParams,
  ExtendedDataSummary
} from './extended-data'

// 重新导出系统监控 API
export { MonitorApiClient }
export const monitorApi = monitorApiInst
export type {
  HealthCheckResponse,
  SystemMetrics,
  DatabaseStats,
  ApiPerformance,
  NotificationChannel
} from './monitor'

// 重新导出龙虎榜 API
export { TopListApiClient }
export const topListApi = topListApiInst

// 重新导出龙虎榜机构明细 API
export { TopInstApiClient }
export const topInstApi = topInstApiInst
export type {
  TopListParams,
  TopListItem,
  TopListStatistics
} from './top-list'
export type {
  TopInstParams,
  TopInstItem,
  TopInstStatistics
} from './top-inst'

// 重新导出涨跌停列表 API
export { LimitListApiClient }
export const limitListApi = limitListApiInst
export type {
  LimitListParams,
  LimitListData,
  LimitListStatistics
} from './limit-list'

// 重新导出连板天梯 API
export { LimitStepApiClient }
export const limitStepApi = limitStepApiInst
export type {
  LimitStepParams,
  LimitStepData,
  LimitStepStatistics
} from './limit-step'

// 重新导出最强板块统计 API
export { LimitCptApiClient }
export const limitCptApi = limitCptApiInst
export type {
  LimitCptParams,
  LimitCptData,
  LimitCptStatistics
} from './limit-cpt'

// 重新导出卖方盈利预测数据 API
export { ReportRcApiClient }
export const reportRcApi = reportRcApiInst
export type {
  ReportRcParams,
  ReportRcData,
  ReportRcStatistics,
  TopRatedStock
} from './report-rc'

// 重新导出每日筹码及胜率 API
export { CyqPerfApiClient }
export const cyqPerfApi = cyqPerfApiInst
export type {
  CyqPerfParams,
  CyqPerfData,
  CyqPerfStatistics
} from './cyq-perf-api'

// 重新导出每日筹码分布 API
export { CyqChipsApiClient }
export const cyqChipsApi = cyqChipsApiInst
export type {
  CyqChipsParams,
  CyqChipsData,
  CyqChipsStatistics
} from './cyq-chips-api'

// 重新导出中央结算系统持股汇总 API
export { CcassHoldApiClient }
export const ccassHoldApi = ccassHoldApiInst

// 东方财富板块成分
export { DcMemberApiClient }
export const dcMemberApi = dcMemberApiInst
export type {
  DcMemberParams,
  DcMemberData,
  DcMemberStatistics
} from './dc-member-api'

// 东方财富板块数据
export { DcIndexApiClient }
export const dcIndexApi = dcIndexApiInst
export type {
  DcIndexParams,
  DcIndexData,
  DcIndexStatistics
} from './dc-index-api'

// 东方财富概念板块行情
export { DcDailyApiClient }
export const dcDailyApi = dcDailyApiInst
export type {
  DcDailyParams,
  DcDailyData,
  DcDailyStatistics
} from './dc-daily-api'

// 重新导出中央结算系统持股汇总 API
export type {
  CcassHoldParams,
  CcassHoldData,
  CcassHoldStatistics
} from './ccass-hold-api'

// 重新导出中央结算系统持股明细 API
export { CcassHoldDetailApiClient }
export const ccassHoldDetailApi = ccassHoldDetailApiInst
export type {
  CcassHoldDetailParams,
  CcassHoldDetailData,
  CcassHoldDetailStatistics
} from './ccass-hold-detail-api'

// 重新导出北向资金持股 API
export { HkHoldApiClient }
export const hkHoldApi = hkHoldApiInst
export type {
  HkHoldQueryParams,
  HkHoldData,
  HkHoldStatistics
} from './hk-hold-api'

// 重新导出股票开盘集合竞价 API
export { StkAuctionOApiClient }
export const stkAuctionOApi = stkAuctionOApiInst
export type {
  StkAuctionOParams,
  StkAuctionOData,
  StkAuctionOStatistics
} from './stk-auction-o'

// 重新导出股票收盘集合竞价 API
export { StkAuctionCApiClient }
export const stkAuctionCApi = stkAuctionCApiInst
export type {
  StkAuctionCParams,
  StkAuctionCData,
  StkAuctionCStatistics
} from './stk-auction-c'

// 重新导出神奇九转指标 API
export { StkNineturnApiClient }
export const stkNineturnApi = stkNineturnApiInst
export type {
  StkNineturnParams,
  StkNineturnData,
  StkNineturnStatistics,
  TurnSignal
} from './stk-nineturn-api'

// 重新导出AH股比价 API
export { StkAhComparisonApiClient }
export const stkAhComparisonApi = stkAhComparisonApiInst
export type {
  StkAhComparisonParams,
  StkAhComparisonData,
  StkAhComparisonStatistics,
  TopPremiumParams,
  SyncAsyncParams
} from './stk-ah-comparison'

// 重新导出机构调研表 API
export { StkSurvApiClient }
export const stkSurvApi = stkSurvApiInst
export type {
  StkSurvParams,
  StkSurvData,
  StkSurvStatistics
} from './stk-surv-api'

// 重新导出券商每月荐股 API
import { BrokerRecommendApiClient, brokerRecommendApi as brokerRecommendApiInst } from './broker-recommend-api'
export { BrokerRecommendApiClient }
export const brokerRecommendApi = brokerRecommendApiInst
export type {
  BrokerRecommendParams,
  BrokerRecommendData,
  BrokerRecommendStatistics
} from './broker-recommend-api'

// 重新导出交易日历 API
export { TradeCalApiClient }
export const tradeCalApi = tradeCalApiInst
export type {
  TradeCalParams,
  TradeCalData,
  TradeCalStatistics,
  TradeCalSyncParams
} from './trade-cal-api'

// 重新导出个股异常波动 API
export { StkShockApiClient }
export const stkShockApi = stkShockApiInst
export type {
  StkShockParams,
  StkShockData,
  StkShockStatistics
} from './stk-shock'

// 重新导出交易所重点提示证券 API
export { StkAlertApiClient }
export const stkAlertApi = stkAlertApiInst
export type {
  StkAlertParams,
  StkAlertData,
  StkAlertStatistics
} from './stk-alert'

// 重新导出个股严重异常波动 API
export { StkHighShockApiClient }
export const stkHighShockApi = stkHighShockApiInst
export type {
  StkHighShockParams,
  StkHighShockData,
  StkHighShockStatistics
} from './stk-high-shock'

// 重新导出业绩预告 API
export { ForecastApiClient }
export const forecastApi = forecastApiInst
export type {
  ForecastParams,
  ForecastData,
  ForecastStatistics
} from './forecast'

// 重新导出股票回购 API
export { RepurchaseApiClient }
export const repurchaseApi = repurchaseApiInst
export type {
  RepurchaseParams,
  RepurchaseData,
  RepurchaseStatistics
} from './repurchase'

// 重新导出限售股解禁 API
export { ShareFloatApiClient }
export const shareFloatApi = shareFloatApiInst
export type {
  ShareFloatParams,
  ShareFloatData,
  ShareFloatStatistics
} from './share-float'

// 重新导出股东人数 API
export { StkHolderNumberApiClient }
export const stkHolderNumberApi = stkHolderNumberApiInst
export type {
  StkHolderNumberParams,
  StkHolderNumberData,
  StkHolderNumberStatistics
} from './stk-holdernumber'

// 重新导出大宗交易 API
export { BlockTradeApiClient }
export const blockTradeApi = blockTradeApiInst
export type {
  BlockTradeParams,
  BlockTradeData,
  BlockTradeStatistics
} from './block-trade'

// 重新导出股东增减持 API
export { StkHoldertradeApiClient }
export const stkHoldertradeApi = stkHoldertradeApiInst
export type {
  StkHoldertradeParams,
  StkHoldertradeData,
  StkHoldertradeStatistics,
  StkHoldertradeListResponse,
  SyncStkHoldertradeParams
} from './stk-holdertrade-api'

// 重新导出利润表 API
export { IncomeApiClient }
export const incomeApi = incomeApiInst
export type {
  IncomeDataParams,
  IncomeData,
  IncomeStatistics
} from './income-api'

// 重新导出资产负债表 API
export { BalancesheetApiClient }
export const balancesheetApi = balancesheetApiInst
export type {
  BalancesheetDataParams,
  BalancesheetData,
  BalancesheetStatistics
} from './balancesheet-api'

// 重新导出现金流量表 API
export { CashflowApiClient }
export const cashflowApi = cashflowApiInst
export type {
  CashflowQueryParams,
  CashflowData,
  CashflowStatistics
} from './cashflow-api'

// 重新导出业绩快报 API
export { ExpressApiClient }
export const expressApi = expressApiInst
export type {
  ExpressParams,
  ExpressData,
  ExpressStatistics
} from './express'

// 重新导出分红送股 API
export { FinancialDataApiClient }
export const financialDataApi = financialDataApiInst
export type {
  DividendData,
  DividendStatistics,
  DividendParams,
  FinaMainbzData,
  FinaMainbzStatistics,
  FinaMainbzParams,
} from './financial-data'

// 重新导出停复牌 API
export { SuspendApiClient }
export const suspendApi = suspendApiInst
export type {
  SuspendData,
  SuspendStatistics,
  SuspendListParams,
  SuspendSyncParams
} from './suspend'

// 重新导出每日涨跌停价格 API
export { StkLimitDApiClient }
export const stkLimitDApi = stkLimitDApiInst
export type {
  StkLimitDData,
  StkLimitDStatistics,
  StkLimitDParams
} from './stk-limit-d'

// 重新导出复权因子 API
export { AdjFactorApiClient }
export const adjFactorApi = adjFactorApiInst
export type {
  AdjFactorData,
  AdjFactorStatistics,
  AdjFactorParams
} from './adj-factor-api'

// 重新导出新股列表 API
export { NewStockApiClient }
export const newStockApi = newStockApiInst
export type {
  NewStockData,
  NewStockStatistics,
  NewStockParams
} from './new-stock-api'

// 重新导出股票列表 API
export { StockListApiClient }
export const stockListApi = stockListApiInst
export type {
  StockListData,
  StockListStatistics,
  StockListParams as StockListQueryParams
} from './stock-list-api'

// 重新导出股票日线数据 API
export { StockDailyApiClient }
export const stockDailyApi = stockDailyApiInst
export type {
  StockDailyData,
  StockDailyStatistics,
  StockDailyParams,
  SyncDailyParams,
  FullHistoryProgressData
} from './stock-daily'

// 重新导出ST股票列表 API
export { StockStApiClient }
export const stockStApi = stockStApiInst
export type {
  StockStData,
  StockStParams,
  StockStStatistics,
  StockStResponse,
  StockStTypeDistribution
} from './stock-st-api'

// 重新导出同步仪表盘 API
export { SyncDashboardApiClient }
export const syncDashboardApi = syncDashboardApiInst
export type {
  SyncConfig,
  SyncOverviewItem,
  SyncOverviewResponse,
  SyncConfigUpdate,
  LastTaskRecord,
  RedisProgress,
  CategoryStat,
} from './sync-dashboard'

// 重新导出股票AI分析 API
export { StockAiAnalysisApiClient }
export const stockAiAnalysisApi = stockAiAnalysisApiInst
export type {
  StockAiAnalysisParams,
  StockAiAnalysisData,
} from './stock-ai-analysis'

// 重新导出数据操作 API
export { DataOpsApiClient }
export const dataOpsApi = dataOpsApiInst
export type { ClearTableParams, ClearTableResult } from './data-ops'

