import axiosInstance, { apiGet, apiPost, apiPut } from './axios-instance'
import type {
  StockInfo,
  StockQuotePanel,
  StockDaily,
  FeatureData,
  Prediction,
  MinuteData,
  Concept,
  ApiResponse,
  PaginatedResponse,
  StockList,
  StockListItem,
  StockAnalysisRecord,
} from '@/types'

// ========== 股票相关API ==========

export async function getStockList(params?: {
  market?: string
  list_status?: string
  skip?: number
  limit?: number
  search?: string
  concept_code?: string
  industry?: string
  sort_by?: string
  sort_order?: string
  stock_selection_strategy_id?: number
  user_stock_list_id?: number
  ts_codes?: string
  include_analysis?: boolean
}): Promise<PaginatedResponse<StockInfo> & { strategy_name?: string }> {
  const response = await axiosInstance.get('/api/stocks/list', { params })
  const result = response.data as ApiResponse<PaginatedResponse<StockInfo>>
  return result.data || { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }
}

export async function getStockIndustries(): Promise<{ value: string; label: string; count: number }[]> {
  const response = await axiosInstance.get('/api/stocks/list/industries')
  const result = response.data as ApiResponse<{ industries: { value: string; label: string; count: number }[] }>
  return result.data?.industries || []
}

export async function getConceptBoards(params?: {
  search?: string
  idx_type?: string
  limit?: number
  offset?: number
}): Promise<{ items: { ts_code: string; name: string; member_count: number }[]; total: number }> {
  const response = await axiosInstance.get('/api/stocks/list/concepts', { params })
  const result = response.data as ApiResponse<{ items: { ts_code: string; name: string; member_count: number }[]; total: number }>
  return result.data || { items: [], total: 0 }
}

export async function getStock(code: string): Promise<StockInfo> {
  const response = await axiosInstance.get(`/api/stocks/list`, {
    params: { search: code, limit: 20, list_status: 'L', include_analysis: true }
  })
  const result = response.data as ApiResponse<PaginatedResponse<StockInfo>>
  if (result.data?.items && result.data.items.length > 0) {
    const exact = result.data.items.find(s => s.code === code)
    return exact ?? result.data.items[0]
  }
  throw new Error(`Stock ${code} not found`)
}

export async function getStockQuotePanel(code: string): Promise<StockQuotePanel | null> {
  try {
    const response = await axiosInstance.get(`/api/stocks/${code}/quote-panel`)
    const result = response.data as ApiResponse<StockQuotePanel>
    return result.data ?? null
  } catch {
    return null
  }
}

export async function getStockBasicInfo(code: string): Promise<StockInfo | null> {
  try {
    const response = await axiosInstance.get(`/api/stocks/${code}/basic-info`)
    const result = response.data as ApiResponse<StockInfo>
    return result.data ?? null
  } catch {
    return null
  }
}

export async function getChipsDistribution(tsCode: string): Promise<{ price: number; percent: number; trade_date?: string }[]> {
  try {
    const response = await axiosInstance.get('/api/cyq-chips/distribution', { params: { ts_code: tsCode } })
    const result = response.data
    if (result.code === 200 && result.data?.items) {
      return result.data.items.map((item: { price: number; percent: number; trade_date?: string }) => ({
        price: item.price,
        percent: item.percent,
        trade_date: item.trade_date,
      }))
    }
    return []
  } catch {
    return []
  }
}

/**
 * 批量获取指定日期范围的筹码分布历史
 * 返回按 trade_date 分组的 Map<YYYY-MM-DD, ChipItem[]>
 * 用于 K 线图 hover 联动：鼠标滑过某个交易日，瞬间切换到该日的筹码分布
 *
 * @param tsCode 股票代码（如 000001.SZ）
 * @param startDate 起始日期 YYYY-MM-DD
 * @param endDate 结束日期 YYYY-MM-DD
 */
export async function getChipsDistributionHistory(
  tsCode: string,
  startDate: string,
  endDate: string
): Promise<Map<string, { price: number; percent: number }[]>> {
  const result = new Map<string, { price: number; percent: number }[]>()
  try {
    const response = await axiosInstance.get('/api/cyq-chips', {
      params: {
        ts_code: tsCode,
        start_date: startDate,
        end_date: endDate,
        page: 1,
        page_size: 50000,  // 后端上限，单只股票 60 交易日约 6000 行
        sort_by: 'trade_date',
        sort_order: 'asc',
      },
    })
    const payload = response.data
    if (payload.code !== 200 || !payload.data?.items) return result

    for (const item of payload.data.items as Array<{ trade_date: string; price: number; percent: number }>) {
      // 后端 trade_date 为 YYYYMMDD；归一化为 YYYY-MM-DD 便于前端按 K 线日期直接匹配
      const raw = String(item.trade_date)
      const key = raw.length === 8
        ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
        : raw
      const bucket = result.get(key)
      if (bucket) {
        bucket.push({ price: Number(item.price), percent: Number(item.percent) })
      } else {
        result.set(key, [{ price: Number(item.price), percent: Number(item.percent) }])
      }
    }
  } catch {
    // 失败时返回空 Map，调用方退化为"只显示最新一日筹码"
  }
  return result
}

export async function getStockCodes(params?: {
  market?: string
  exchange?: string
  industry?: string
  status?: string
  search?: string
  concept_code?: string
  stock_selection_strategy_id?: number
  list_status?: string
  user_stock_list_id?: number
  limit?: number
}): Promise<{ codes: string[]; total: number }> {
  const response = await axiosInstance.get('/api/stocks/codes/filtered', { params })
  const result = response.data as ApiResponse<{ codes: string[]; total: number }>
  return result.data || { codes: [], total: 0 }
}

export async function updateStockList(): Promise<ApiResponse<{ total: number }>> {
  return apiPost('/api/stocks/update')
}

// ========== 概念相关API ==========

export async function getConceptsList(params?: {
  limit?: number
  search?: string
}): Promise<{ items: Concept[]; total: number }> {
  const response = await axiosInstance.get('/api/concepts/list', { params })
  return response.data.data || { items: [], total: 0 }
}

export async function getConcept(conceptId: number): Promise<Concept> {
  const response = await axiosInstance.get(`/api/concepts/${conceptId}`)
  return response.data.data
}

export async function getConceptStocks(conceptId: number, limit?: number): Promise<{ items: StockInfo[]; total: number }> {
  const response = await axiosInstance.get(`/api/concepts/${conceptId}/stocks`, {
    params: { limit }
  })
  return response.data.data || { items: [], total: 0 }
}

export async function getStockConcepts(stockCode: string): Promise<Concept[]> {
  const response = await axiosInstance.get(`/api/concepts/stock/${stockCode}`)
  return response.data.data || []
}

export async function syncConcepts(source: string = 'ths'): Promise<ApiResponse<{ count: number }>> {
  return apiPost('/api/concepts/sync', null, { params: { source } })
}

export async function updateStockConcepts(stockCode: string, conceptIds: number[]): Promise<ApiResponse<{ count: number }>> {
  return apiPut(`/api/concepts/stock/${stockCode}/concepts`, { concept_ids: conceptIds })
}

// ========== 数据相关API ==========

export async function getDailyData(
  code: string,
  params?: { start_date?: string; end_date?: string }
): Promise<StockDaily[]> {
  const response = await axiosInstance.get(`/api/data/daily/${code}`, { params })
  return response.data.data
}

export async function downloadData(params: {
  stock_codes: string[]
  years?: number
}): Promise<ApiResponse<{ task_id: string }>> {
  return apiPost('/api/data/download', params)
}

// ========== 特征相关API ==========

export async function getFeatures(
  code: string,
  params?: {
    feature_type?: string
    limit?: number
    end_date?: string
  }
): Promise<{
  code: string
  feature_type: string
  total: number
  returned: number
  has_more: boolean
  columns: string[]
  data: FeatureData[]
}> {
  const response = await axiosInstance.get(`/api/features/${code}`, { params })
  return response.data.data
}

export async function calculateFeatures(
  code: string,
  params?: { feature_types?: string[] }
): Promise<ApiResponse<{ message: string }>> {
  return apiPost(`/api/features/calculate/${code}`, params)
}

// ========== 分时数据相关API ==========

export async function getMinuteData(
  code: string,
  date?: string,
  forceRefresh: boolean = false
): Promise<ApiResponse<{
  code: string
  date: string
  records: MinuteData[]
  from_cache: boolean
  completeness?: number
  record_count: number
}>> {
  const params: Record<string, string | boolean> = {}
  if (date) params.date = date
  if (forceRefresh) params.force_refresh = true

  const response = await axiosInstance.get(`/api/stocks/${code}/minute`, { params })
  return response.data
}

export async function getMinuteDataRange(
  code: string,
  period: string = '5',
  startDate?: string,
  endDate?: string,
  limit: number = 1000
): Promise<ApiResponse<{
  code: string
  period: string
  start_date: string
  end_date: string
  records: MinuteData[]
  record_count: number
}>> {
  const params: Record<string, string | number> = { period, limit }
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate

  const response = await axiosInstance.get(`/api/stocks/${code}/minute/range`, { params })
  return response.data
}

export async function getPrediction(
  code: string,
  params?: { model_name?: string }
): Promise<Prediction> {
  const response = await axiosInstance.get(`/api/models/predict/${code}`, { params })
  return response.data
}

// ========== 用户股票列表（自选股）API ==========

export async function getUserStockLists(): Promise<ApiResponse<{ items: StockList[]; total: number }>> {
  return apiGet('/api/user-stock-lists')
}

export async function createStockList(name: string, description?: string): Promise<ApiResponse<StockList>> {
  return apiPost('/api/user-stock-lists', { name, description })
}

export async function renameStockList(listId: number, name: string, description?: string): Promise<ApiResponse<StockList>> {
  return apiPut(`/api/user-stock-lists/${listId}`, { name, description })
}

export async function deleteStockList(listId: number): Promise<ApiResponse<null>> {
  const response = await axiosInstance.delete(`/api/user-stock-lists/${listId}`)
  return response.data
}

export async function getStockListItems(listId: number): Promise<ApiResponse<{ items: StockListItem[]; total: number }>> {
  return apiGet(`/api/user-stock-lists/${listId}/items`)
}

export async function getStockListTsCodes(listId: number): Promise<ApiResponse<{ ts_codes: string[] }>> {
  return apiGet(`/api/user-stock-lists/${listId}/ts-codes`)
}

export async function addStocksToList(listId: number, tsCodes: string[]): Promise<ApiResponse<{ added: number; skipped: number }>> {
  return apiPost(`/api/user-stock-lists/${listId}/items`, { ts_codes: tsCodes })
}

export async function removeStocksFromList(listId: number, tsCodes: string[]): Promise<ApiResponse<{ removed: number }>> {
  const response = await axiosInstance.delete(`/api/user-stock-lists/${listId}/items`, {
    data: { ts_codes: tsCodes },
  })
  return response.data
}

// ========== 股票AI分析 ==========

export async function saveStockAnalysis(params: {
  ts_code: string
  analysis_type: string
  analysis_text: string
  score?: number
  prompt_text?: string
  ai_provider?: string
  ai_model?: string
}): Promise<ApiResponse<{ id: number }>> {
  return apiPost('/api/stock-ai-analysis/', params)
}

export async function getLatestStockAnalysis(tsCode: string, analysisType: string): Promise<ApiResponse<{ id: number; score: number | null; version: number; analysis_text: string; created_at: string }>> {
  return apiGet('/api/stock-ai-analysis/latest', { params: { ts_code: tsCode, analysis_type: analysisType } })
}

export async function getStockAnalysisHistory(
  tsCode: string,
  analysisType: string,
  limit = 50,
  offset = 0
): Promise<ApiResponse<{ items: StockAnalysisRecord[]; total: number }>> {
  return apiGet('/api/stock-ai-analysis/history', {
    params: { ts_code: tsCode, analysis_type: analysisType, limit, offset },
  })
}

export async function updateStockAnalysis(
  recordId: number,
  params: { analysis_text: string; score?: number }
): Promise<ApiResponse<{ id: number }>> {
  return apiPut(`/api/stock-ai-analysis/${recordId}`, params)
}

export async function deleteStockAnalysis(recordId: number): Promise<ApiResponse<{ id: number }>> {
  const response = await axiosInstance.delete(`/api/stock-ai-analysis/${recordId}`)
  return response.data
}

export async function generateStockAnalysis(params: {
  ts_code: string
  stock_name: string
  stock_code: string
  analysis_type: string
  template_key: string
}): Promise<ApiResponse<{ analysis_text: string; score?: number }>> {
  return apiPost('/api/stock-ai-analysis/generate', params)
}

export async function generateReviewAnalysis(params: {
  ts_code: string
  stock_name: string
  stock_code: string
  original_analysis_id: number
  review_type?: 'hot_money' | 'midline' | 'longterm'
  force?: boolean
}): Promise<ApiResponse<{
  analysis_text: string
  score?: number
  original_analysis_id: number
  original_analysis_date: string
  days_since_original: number | null
  review_type: string
}>> {
  return apiPost('/api/stock-ai-analysis/generate-review', params)
}

export async function generateMultiAnalysis(params: {
  ts_code: string
  stock_name: string
  stock_code: string
  analysis_types: string[]
  include_cio?: boolean
}): Promise<ApiResponse<{ celery_task_id: string; ts_code: string }>> {
  // /generate-multi 已改为异步：提交任务后返回 celery_task_id，由调用方轮询 /batch/{id} 取进度
  return apiPost('/api/stock-ai-analysis/generate-multi', params)
}

export async function getActiveTaskByTsCode(
  tsCode: string,
): Promise<ApiResponse<{ celery_task_id: string | null }>> {
  return apiGet(`/api/stock-ai-analysis/active/by-ts-code/${encodeURIComponent(tsCode)}`)
}

// ===== 批量 AI 分析 =====

export interface BatchAnalysisItem {
  ts_code: string
  stock_name: string
  status: 'pending' | 'running' | 'success' | 'error'
  error?: string | null
  duration_sec?: number | null
  expert_count?: number
}

export interface BatchAnalysisProgress {
  celery_task_id: string
  status: string
  progress: number
  total_items: number | null
  completed_items: number | null
  success_items: number | null
  failed_items: number | null
  items: BatchAnalysisItem[]
  created_at: string | null
  completed_at: string | null
  error: string | null
}

export async function submitBatchAnalysis(params: {
  ts_codes: string[]
  analysis_types?: string[]
  include_cio?: boolean
}): Promise<ApiResponse<{ celery_task_id: string; total: number; ts_codes: string[] }>> {
  return apiPost('/api/stock-ai-analysis/batch', params)
}

export async function getBatchAnalysisProgress(
  celeryTaskId: string,
): Promise<ApiResponse<BatchAnalysisProgress>> {
  return apiGet(`/api/stock-ai-analysis/batch/${celeryTaskId}`)
}

export async function getActiveBatchTsCodes(): Promise<ApiResponse<{ ts_codes: string[] }>> {
  return apiGet('/api/stock-ai-analysis/batch/active/ts-codes')
}

export async function collectStockData(tsCode: string, stockName: string): Promise<ApiResponse<{ text: string }>> {
  return apiPost('/api/stock-data-collection/collect', {
    ts_code: tsCode,
    stock_name: stockName,
    format: 'text',
  })
}

export async function getPromptTemplateByKey(
  templateKey: string,
  params?: { stock_name?: string; stock_code?: string; ts_code?: string }
): Promise<ApiResponse<{ content: string; key: string; name: string }>> {
  return apiGet(`/api/prompt-templates/by-key/${templateKey}`, { params })
}
