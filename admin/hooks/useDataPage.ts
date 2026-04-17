/**
 * useDataPage — 数据页面通用 Hook
 *
 * 将 70+ 数据页面的公共逻辑（加载、分页、同步、清空、回调清理）收敛为配置化调用。
 * 页面只需提供：列定义、统计卡片、筛选器等个性化部分。
 *
 * 基本用法：
 * ```ts
 * const dp = useDataPage<MyData, MyStats>({
 *   apiCall: (params) => myApi.getData(params),
 *   taskName: 'tasks.sync_my_table',
 *   syncFn: (params) => myApi.syncAsync(params),
 *   bulkOps: {
 *     tableKey: 'my_table',
 *     syncFn: (p) => myApi.syncFullHistory(p),
 *     taskName: 'tasks.sync_my_table_full_history',
 *   },
 * })
 * ```
 *
 * 支持的模式：
 * - offset/limit 分页（默认）或 page/page_size 分页
 * - 服务端排序（sort_by + sort_order）
 * - 独立的统计 API 调用（statisticsCall）
 * - 同步弹窗日期参数
 * - 后端回填日期（backfillDateField）
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { useTaskStore, type Task } from '@/stores/task-store'
import { useDataBulkOps, type DataBulkOpsOptions } from '@/hooks/useDataBulkOps'
import { toDateStr } from '@/lib/date-utils'

// --------------- 类型定义 ---------------

/**
 * apiCall 使用宽松类型以兼容各种后端返回结构（trade_date: string | null 等）。
 * 实际运行时，hook 内部按 items > data 优先级读取数据列表。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LooseApiCall = (params: Record<string, unknown>) => Promise<ApiResponse<any>>

/** 标准 API 响应 */
interface ApiResponse<P> {
  code: number
  message?: string
  data?: P
}

/** 同步接口响应 */
interface SyncResponse {
  code: number
  message?: string
  data?: {
    celery_task_id: string
    task_name: string
    display_name: string
  }
}

/** 分页模式 */
type PaginationMode = 'offset' | 'page'

/** useDataPage 配置 */
export interface UseDataPageOptions<T, S = unknown> {
  /**
   * 主数据 API 调用。
   * Hook 会自动注入分页/排序参数，你只需要添加业务筛选参数。
   *
   * params 已包含：分页参数 + 排序参数（如果启用）
   */
  apiCall: LooseApiCall

  /**
   * 独立的统计 API（可选）。
   * 部分页面的统计数据由独立接口返回（如 financial 系列），而非内联在主数据中。
   * 传入后会与 apiCall 并行调用。
   */
  statisticsCall?: (params: Record<string, unknown>) => Promise<ApiResponse<S>>

  /**
   * 增量同步 API（同步按钮）。
   * 不传则不显示同步按钮相关状态。
   */
  syncFn?: (params: Record<string, unknown>) => Promise<SyncResponse>

  /** Celery 任务名，用于派生 syncing 状态 */
  taskName: string | string[]

  /** 全量同步 + 清空配置（传给 useDataBulkOps） */
  bulkOps?: Omit<DataBulkOpsOptions, 'onSuccess'>

  /** 分页模式，默认 'offset'（offset/limit），'page' 使用 page/page_size */
  paginationMode?: PaginationMode

  /** 每页大小，默认 30 */
  pageSize?: number

  /**
   * 额外的查询参数构建函数。
   * 每次 loadData 时调用，将结果合并到 API 请求参数中。
   * 返回的参数会覆盖 hook 自动生成的分页/排序参数。
   */
  buildParams?: () => Record<string, unknown>

  /**
   * 后端回填日期字段名。
   * 部分页面（如 top-list、ccass-hold）初次加载时不传日期，
   * 后端返回 data.trade_date 后回填到筛选器。
   * 传入此字段 + onBackfillDate 回调即可自动处理。
   */
  backfillDateField?: string

  /** 回填日期回调 */
  onBackfillDate?: (dateStr: string) => void

  /** 同步完成后的成功提示（默认 '数据同步完成'） */
  syncSuccessMessage?: string

  /** 同步完成后的失败提示（默认 '数据同步失败'） */
  syncFailureMessage?: string

  /** 同步提交后的提示（默认 '同步任务已提交'） */
  syncSubmittedMessage?: string

  /** 是否在 mount 时自动加载数据，默认 true */
  autoLoad?: boolean
}

/** useDataPage 返回值 */
export interface UseDataPageReturn<T, S> {
  // ---- 数据状态 ----
  data: T[]
  statistics: S | null
  isLoading: boolean
  total: number
  page: number
  pageSize: number

  // ---- 分页 ----
  /** 加载指定页（或刷新当前页）*/
  loadData: (targetPage?: number) => Promise<void>
  /** 翻页处理（给 DataTable pagination.onPageChange） */
  handlePageChange: (newPage: number) => void
  /** 每页大小变更 */
  handlePageSizeChange: (newSize: number) => void

  // ---- 排序 ----
  sortKey: string | null
  sortDirection: 'asc' | 'desc' | null
  /** 给 DataTable sort.onSort */
  handleSort: (key: string, direction: 'asc' | 'desc' | null) => void

  // ---- 同步状态 ----
  /** 增量同步中（task store 派生） */
  syncing: boolean

  // ---- 同步弹窗 ----
  syncDialogOpen: boolean
  setSyncDialogOpen: (open: boolean) => void
  syncStartDate: Date | undefined
  setSyncStartDate: (d: Date | undefined) => void
  syncEndDate: Date | undefined
  setSyncEndDate: (d: Date | undefined) => void
  /** 确认同步（在弹窗确认按钮中调用） */
  handleSyncConfirm: () => Promise<void>
  /** 直接同步（无弹窗，如 top-list 的同步按钮） */
  handleSyncDirect: (params?: Record<string, unknown>) => Promise<void>

  // ---- 全量同步 & 清空 (useDataBulkOps) ----
  handleFullSync: () => Promise<void>
  handleClear: () => Promise<void>
  fullSyncing: boolean
  isClearing: boolean
  isClearDialogOpen: boolean
  setIsClearDialogOpen: (open: boolean) => void
  earliestHistoryDate: string

  // ---- 查询 ----
  /** 重置到第1页并重新加载（用于筛选器"查询"按钮） */
  handleQuery: () => void
}

// --------------- Hook 实现 ---------------

export function useDataPage<T, S = unknown>(
  options: UseDataPageOptions<T, S>
): UseDataPageReturn<T, S> {
  const {
    apiCall,
    statisticsCall,
    syncFn,
    taskName,
    bulkOps,
    paginationMode = 'offset',
    pageSize: defaultPageSize = 30,
    buildParams,
    backfillDateField = 'trade_date',
    onBackfillDate,
    syncSuccessMessage = '数据同步完成',
    syncFailureMessage = '数据同步失败',
    syncSubmittedMessage = '同步任务已提交',
    autoLoad = true,
  } = options

  // ---- 数据状态 ----
  const [data, setData] = useState<T[]>([])
  const [statistics, setStatistics] = useState<S | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(defaultPageSize)

  // ---- 排序 ----
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // ---- 同步弹窗 ----
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // ---- task store ----
  const {
    addTask,
    triggerPoll,
    registerCompletionCallback,
    unregisterCompletionCallback,
    isTaskRunning,
  } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, (task: Task) => void>>(new Map())

  // 派生同步状态
  const taskNames = Array.isArray(taskName) ? taskName : [taskName]
  const syncing = taskNames.some((name) => isTaskRunning(name))

  // ---- loadData ----
  // 使用 ref 保存最新的排序/分页/参数，避免闭包陷阱
  const sortRef = useRef({ sortKey, sortDirection })
  sortRef.current = { sortKey, sortDirection }

  const loadData = useCallback(
    async (targetPage?: number) => {
      const currentPage = targetPage ?? page
      setIsLoading(true)
      try {
        // 构建分页参数
        const paginationParams: Record<string, unknown> =
          paginationMode === 'offset'
            ? { limit: pageSize, offset: (currentPage - 1) * pageSize }
            : { page: currentPage, page_size: pageSize }

        // 构建排序参数
        const currentSort = sortRef.current
        const sortParams: Record<string, unknown> = {}
        if (currentSort.sortKey) {
          sortParams.sort_by = currentSort.sortKey
          sortParams.sort_order = currentSort.sortDirection ?? 'desc'
        }

        // 合并业务筛选参数
        const extraParams = buildParams?.() ?? {}

        const mergedParams = { ...paginationParams, ...sortParams, ...extraParams }

        // 并行调用数据 API 和统计 API
        const [dataResp, statsResp] = await Promise.all([
          apiCall(mergedParams),
          statisticsCall ? statisticsCall(extraParams) : Promise.resolve(null),
        ])

        if (dataResp.code === 200 && dataResp.data) {
          const payload = dataResp.data
          // items 优先于 data 字段
          setData(payload.items ?? payload.data ?? [])
          setTotal(payload.total ?? 0)
          setPage(currentPage)

          // 内联统计
          if (payload.statistics !== undefined) {
            setStatistics(payload.statistics ?? null)
          }

          // 后端回填日期
          if (onBackfillDate && payload[backfillDateField]) {
            onBackfillDate(payload[backfillDateField] as string)
          }
        } else {
          toast.error(dataResp.message || '获取数据失败')
        }

        // 独立统计响应
        if (statsResp && statsResp.code === 200 && statsResp.data) {
          setStatistics(statsResp.data)
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : '加载数据失败'
        toast.error(message)
      } finally {
        setIsLoading(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiCall, statisticsCall, buildParams, paginationMode, pageSize, page, backfillDateField, onBackfillDate]
  )

  // 稳定引用（供回调注册使用）
  const loadDataRef = useRef(loadData)
  loadDataRef.current = loadData

  // ---- 翻页 ----
  const handlePageChange = useCallback(
    (newPage: number) => {
      loadDataRef.current(newPage)
    },
    []
  )

  const handlePageSizeChange = useCallback(
    (newSize: number) => {
      setPageSize(newSize)
      setPage(1)
      // 下一 tick 用新 pageSize 加载
      setTimeout(() => loadDataRef.current(1), 0)
    },
    []
  )

  // ---- 排序 ----
  const handleSort = useCallback(
    (key: string, direction: 'asc' | 'desc' | null) => {
      const newKey = direction ? key : null
      setSortKey(newKey)
      setSortDirection(direction)
      // 直接用新排序值加载（不依赖 state 更新）
      sortRef.current = { sortKey: newKey, sortDirection: direction }
      loadDataRef.current(1)
    },
    []
  )

  // ---- 查询 ----
  const handleQuery = useCallback(() => {
    loadDataRef.current(1)
  }, [])

  // ---- 注册同步完成回调的公共逻辑 ----
  const registerSyncCallback = useCallback(
    (taskId: string, successMsg: string) => {
      const completionCallback = (task: Task) => {
        if (task.status === 'success') {
          loadDataRef.current(1)
          toast.success(successMsg)
        } else if (task.status === 'failure') {
          toast.error(syncFailureMessage, {
            description: task.error || '同步过程中发生错误',
          })
        }
        unregisterCompletionCallback(taskId, completionCallback)
        activeCallbacksRef.current.delete(taskId)
      }
      activeCallbacksRef.current.set(taskId, completionCallback)
      registerCompletionCallback(taskId, completionCallback)
    },
    [registerCompletionCallback, unregisterCompletionCallback, syncFailureMessage]
  )

  // ---- 同步弹窗确认 ----
  const handleSyncConfirm = useCallback(async () => {
    if (!syncFn) return
    setSyncDialogOpen(false)
    try {
      const params: Record<string, unknown> = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await syncFn(params)
      if (response.code === 200 && response.data) {
        const { celery_task_id: taskId, task_name, display_name } = response.data
        addTask({
          taskId,
          taskName: task_name,
          displayName: display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        registerSyncCallback(taskId, syncSuccessMessage)
        triggerPoll()
        toast.success(syncSubmittedMessage, {
          description: `"${display_name}" 已开始执行，可在任务面板查看进度`,
        })
      } else {
        throw new Error(response.message || '提交同步任务失败')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '提交同步任务失败'
      toast.error(message)
    }
  }, [syncFn, syncStartDate, syncEndDate, addTask, triggerPoll, registerSyncCallback, syncSuccessMessage, syncSubmittedMessage])

  // ---- 直接同步（无弹窗） ----
  const handleSyncDirect = useCallback(
    async (params?: Record<string, unknown>) => {
      if (!syncFn) return
      try {
        const response = await syncFn(params ?? {})
        if (response.code === 200 && response.data) {
          const { celery_task_id: taskId, task_name, display_name } = response.data
          addTask({
            taskId,
            taskName: task_name,
            displayName: display_name,
            taskType: 'data_sync',
            status: 'running',
            progress: 0,
            startTime: Date.now(),
          })
          registerSyncCallback(taskId, syncSuccessMessage)
          triggerPoll()
          toast.success(syncSubmittedMessage)
        } else {
          toast.error(response.message || '提交同步任务失败')
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : '提交同步任务失败'
        toast.error(message)
      }
    },
    [syncFn, addTask, triggerPoll, registerSyncCallback, syncSuccessMessage, syncSubmittedMessage]
  )

  // ---- useDataBulkOps ----
  const bulkOpsResult = useDataBulkOps(
    bulkOps
      ? { ...bulkOps, onSuccess: () => loadDataRef.current(1) }
      : { tableKey: '', syncFn: async () => ({ code: 0 }), taskName: '' }
  )

  // ---- 自动加载 & 清理 ----
  useEffect(() => {
    if (autoLoad) {
      loadDataRef.current(1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
      bulkOpsResult.cleanup()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    // 数据
    data,
    statistics,
    isLoading,
    total,
    page,
    pageSize,

    // 分页
    loadData,
    handlePageChange,
    handlePageSizeChange,

    // 排序
    sortKey,
    sortDirection,
    handleSort,

    // 同步状态
    syncing,

    // 同步弹窗
    syncDialogOpen,
    setSyncDialogOpen,
    syncStartDate,
    setSyncStartDate,
    syncEndDate,
    setSyncEndDate,
    handleSyncConfirm,
    handleSyncDirect,

    // 全量同步 & 清空
    handleFullSync: bulkOpsResult.handleFullSync,
    handleClear: bulkOpsResult.handleClear,
    fullSyncing: bulkOpsResult.fullSyncing,
    isClearing: bulkOpsResult.isClearing,
    isClearDialogOpen: bulkOpsResult.isClearDialogOpen,
    setIsClearDialogOpen: bulkOpsResult.setIsClearDialogOpen,
    earliestHistoryDate: bulkOpsResult.earliestHistoryDate,

    // 查询
    handleQuery,
  }
}
