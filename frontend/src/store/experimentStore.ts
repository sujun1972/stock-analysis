/**
 * 自动化实验Store
 * 使用Zustand管理实验状态
 */

import { create } from 'zustand'

// ==================== 类型定义 ====================

export interface ExperimentBatch {
  batch_id: number
  batch_name: string
  description?: string
  strategy: string
  status: string
  total_experiments: number
  completed_experiments: number
  failed_experiments: number
  running_experiments: number
  success_rate_pct: number
  created_at: string
  started_at?: string
  completed_at?: string
  duration_hours?: number
  avg_rank_score?: number
  max_rank_score?: number
  top_model_id?: string
}

export interface Experiment {
  id: number
  experiment_name: string
  model_id?: string
  config: any
  train_metrics?: any
  backtest_metrics?: any
  rank_score?: number
  rank_position?: number
  status: string
  error_message?: string
}

export interface TopModel {
  experiment_id: number
  model_id: string
  rank_score?: number
  annual_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  config: any
}

export interface BatchConfig {
  batch_name: string
  param_space?: any
  template?: string
  strategy: string
  max_experiments?: number
  description?: string
  config?: {
    max_workers?: number
    auto_backtest?: boolean
    save_models?: boolean
  }
  tags?: string[]
}

// ==================== Store接口 ====================

interface ExperimentStore {
  // 状态
  batches: ExperimentBatch[]
  currentBatch: ExperimentBatch | null
  experiments: Experiment[]
  topModels: TopModel[]
  loading: boolean
  error: string | null

  // 批次操作
  fetchBatches: () => Promise<void>
  fetchBatchInfo: (batchId: number) => Promise<void>
  createBatch: (config: BatchConfig) => Promise<number>
  startBatch: (batchId: number, maxWorkers?: number) => Promise<void>
  cancelBatch: (batchId: number) => Promise<void>
  deleteBatch: (batchId: number) => Promise<void>

  // 实验查询
  fetchExperiments: (batchId: number, status?: string) => Promise<void>
  fetchTopModels: (batchId: number, topN?: number, filters?: any) => Promise<void>

  // 实时监控
  subscribeToProgress: (batchId: number) => void
  unsubscribeFromProgress: () => void

  // 辅助方法
  setError: (error: string | null) => void
  clearError: () => void
  reset: () => void
}

// ==================== API基础URL ====================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ==================== Store实现 ====================

export const useExperimentStore = create<ExperimentStore>((set, get) => ({
  // 初始状态
  batches: [],
  currentBatch: null,
  experiments: [],
  topModels: [],
  loading: false,
  error: null,

  // ==================== 批次操作 ====================

  fetchBatches: async () => {
    try {
      set({ loading: true, error: null })

      const response = await fetch(`${API_BASE_URL}/api/experiment/batches?limit=50`)
      const data = await response.json()

      if (data.status === 'success') {
        set({ batches: data.data.batches, loading: false })
      } else {
        throw new Error(data.message || '获取批次列表失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('fetchBatches error:', error)
    }
  },

  fetchBatchInfo: async (batchId: number) => {
    try {
      set({ loading: true, error: null })

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}`)
      const data = await response.json()

      if (data.status === 'success') {
        set({ currentBatch: data.data, loading: false })
      } else {
        throw new Error(data.message || '获取批次信息失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('fetchBatchInfo error:', error)
    }
  },

  createBatch: async (config: BatchConfig) => {
    try {
      set({ loading: true, error: null })

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      })

      const data = await response.json()

      if (data.status === 'success') {
        const batchId = data.data.batch_id
        set({ loading: false })

        // 刷新批次列表
        await get().fetchBatches()

        return batchId
      } else {
        throw new Error(data.detail || data.message || '创建批次失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('createBatch error:', error)
      throw error
    }
  },

  startBatch: async (batchId: number, maxWorkers?: number) => {
    try {
      set({ loading: true, error: null })

      const body = maxWorkers ? { max_workers: maxWorkers } : {}

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      if (data.status === 'success') {
        set({ loading: false })

        // 刷新批次信息
        await get().fetchBatchInfo(batchId)
      } else {
        throw new Error(data.detail || '启动批次失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('startBatch error:', error)
      throw error
    }
  },

  cancelBatch: async (batchId: number) => {
    try {
      set({ loading: true, error: null })

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}/cancel`, {
        method: 'POST',
      })

      const data = await response.json()

      if (data.status === 'success') {
        set({ loading: false })

        // 刷新批次列表
        await get().fetchBatches()
      } else {
        throw new Error(data.detail || '取消批次失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('cancelBatch error:', error)
      throw error
    }
  },

  deleteBatch: async (batchId: number) => {
    try {
      set({ loading: true, error: null })

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}`, {
        method: 'DELETE',
      })

      const data = await response.json()

      if (data.status === 'success') {
        set({ loading: false })

        // 刷新批次列表
        await get().fetchBatches()
      } else {
        throw new Error(data.detail || '删除批次失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('deleteBatch error:', error)
      throw error
    }
  },

  // ==================== 实验查询 ====================

  fetchExperiments: async (batchId: number, status?: string) => {
    try {
      set({ loading: true, error: null })

      let url = `${API_BASE_URL}/api/experiment/batch/${batchId}/experiments?limit=100`
      if (status) {
        url += `&status=${status}`
      }

      const response = await fetch(url)
      const data = await response.json()

      if (data.status === 'success') {
        set({ experiments: data.data.experiments, loading: false })
      } else {
        throw new Error(data.message || '获取实验列表失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('fetchExperiments error:', error)
    }
  },

  fetchTopModels: async (batchId: number, topN: number = 10, filters?: any) => {
    try {
      set({ loading: true, error: null })

      const params = new URLSearchParams({
        top_n: topN.toString(),
      })

      if (filters?.min_sharpe) params.append('min_sharpe', filters.min_sharpe.toString())
      if (filters?.max_drawdown) params.append('max_drawdown', filters.max_drawdown.toString())
      if (filters?.min_annual_return) params.append('min_annual_return', filters.min_annual_return.toString())

      const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}/top-models?${params}`)
      const data = await response.json()

      if (data.status === 'success') {
        set({ topModels: data.data.models, loading: false })
      } else {
        throw new Error(data.message || '获取Top模型失败')
      }
    } catch (error: any) {
      set({ error: error.message, loading: false })
      console.error('fetchTopModels error:', error)
    }
  },

  // ==================== 实时监控 ====================

  subscribeToProgress: (batchId: number) => {
    const eventSource = new EventSource(`${API_BASE_URL}/api/experiment/batch/${batchId}/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        set({ currentBatch: data })

        // 如果批次完成，关闭连接
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          eventSource.close()
        }
      } catch (error) {
        console.error('SSE parse error:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      eventSource.close()
    }

    // 保存引用以便取消订阅
    ;(window as any).__experimentEventSource = eventSource
  },

  unsubscribeFromProgress: () => {
    const eventSource = (window as any).__experimentEventSource
    if (eventSource) {
      eventSource.close()
      delete (window as any).__experimentEventSource
    }
  },

  // ==================== 辅助方法 ====================

  setError: (error: string | null) => {
    set({ error })
  },

  clearError: () => {
    set({ error: null })
  },

  reset: () => {
    set({
      batches: [],
      currentBatch: null,
      experiments: [],
      topModels: [],
      loading: false,
      error: null,
    })
  },
}))

// ==================== 导出辅助函数 ====================

/**
 * 获取模板列表
 */
export async function fetchTemplates() {
  const response = await fetch(`${API_BASE_URL}/api/experiment/templates`)
  const data = await response.json()
  return data.status === 'success' ? data.data : {}
}

/**
 * 生成实验报告
 */
export async function generateReport(batchId: number) {
  const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}/report`)
  const data = await response.json()
  return data.status === 'success' ? data.data : null
}

/**
 * 获取参数重要性
 */
export async function fetchParameterImportance(batchId: number) {
  const response = await fetch(`${API_BASE_URL}/api/experiment/batch/${batchId}/parameter-importance`)
  const data = await response.json()
  return data.status === 'success' ? data.data : null
}
