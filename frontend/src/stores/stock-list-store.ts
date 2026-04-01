/**
 * 用户股票列表 Store（自选股）
 * 管理用户的自选股列表状态，支持创建、删除、重命名列表，以及批量添加/移除股票
 */

import { create } from 'zustand'
import { apiClient } from '@/lib/api-client'
import type { StockList, StockListItem } from '@/types'

interface StockListState {
  // 用户所有列表
  lists: StockList[]
  // 当前激活的列表 ID（null 表示没有激活任何列表）
  activeListId: number | null
  // 当前激活列表中的股票（含行情）
  activeListItems: StockListItem[]
  // 当前激活列表中股票的 ts_code Set（快速查询是否在列表中）
  activeListCodes: Set<string>

  // 加载状态
  isLoadingLists: boolean
  isLoadingItems: boolean
  error: string | null
}

interface StockListActions {
  // 拉取所有列表
  fetchLists: () => Promise<void>
  // 激活某个列表（并加载成分股）
  setActiveList: (listId: number | null) => Promise<void>
  // 刷新当前激活列表的成分股（用于增删后同步）
  refreshActiveListItems: () => Promise<void>
  // 创建列表
  createList: (name: string, description?: string) => Promise<StockList>
  // 重命名/修改描述
  updateList: (listId: number, name: string, description?: string) => Promise<void>
  // 删除列表
  deleteList: (listId: number) => Promise<void>
  // 批量添加股票到指定列表
  addStocks: (listId: number, tsCodes: string[]) => Promise<{ added: number; skipped: number }>
  // 批量从指定列表移除股票
  removeStocks: (listId: number, tsCodes: string[]) => Promise<{ removed: number }>
  // 清空所有状态（登出时调用）
  reset: () => void
  // 检查指定股票是否在当前激活列表中
  isInActiveList: (tsCode: string) => boolean
}

export type StockListStore = StockListState & StockListActions

const initialState: StockListState = {
  lists: [],
  activeListId: null,
  activeListItems: [],
  activeListCodes: new Set(),
  isLoadingLists: false,
  isLoadingItems: false,
  error: null,
}

export const useStockListStore = create<StockListStore>()((set, get) => ({
  ...initialState,

  fetchLists: async () => {
    set({ isLoadingLists: true, error: null })
    try {
      const res = await apiClient.getUserStockLists()
      const lists = res.data?.items ?? []
      set({ lists, isLoadingLists: false })

      // 如果当前激活的列表已被删除，重置激活状态
      const { activeListId } = get()
      if (activeListId !== null && !lists.find((l) => l.id === activeListId)) {
        set({ activeListId: null, activeListItems: [], activeListCodes: new Set() })
      }
    } catch (err: any) {
      set({ isLoadingLists: false, error: err.message || '获取列表失败' })
    }
  },

  setActiveList: async (listId: number | null) => {
    if (listId === null) {
      set({ activeListId: null, activeListItems: [], activeListCodes: new Set() })
      return
    }
    set({ activeListId: listId, isLoadingItems: true, error: null })
    try {
      const res = await apiClient.getStockListItems(listId)
      const items = res.data?.items ?? []
      set({
        activeListItems: items,
        activeListCodes: new Set(items.map((i) => i.ts_code)),
        isLoadingItems: false,
      })
    } catch (err: any) {
      set({ isLoadingItems: false, error: err.message || '获取列表股票失败' })
    }
  },

  refreshActiveListItems: async () => {
    const { activeListId } = get()
    if (activeListId === null) return
    try {
      const res = await apiClient.getStockListItems(activeListId)
      const items = res.data?.items ?? []
      set({
        activeListItems: items,
        activeListCodes: new Set(items.map((i) => i.ts_code)),
      })
    } catch {
      // 静默失败
    }
  },

  createList: async (name: string, description?: string) => {
    const res = await apiClient.createStockList(name, description)
    if (!res.data) throw new Error(res.message || '创建失败')
    const newList = res.data
    set((state) => ({ lists: [...state.lists, newList] }))
    return newList
  },

  updateList: async (listId: number, name: string, description?: string) => {
    await apiClient.renameStockList(listId, name, description)
    set((state) => ({
      lists: state.lists.map((l) =>
        l.id === listId ? { ...l, name, description: description ?? l.description } : l
      ),
    }))
  },

  deleteList: async (listId: number) => {
    await apiClient.deleteStockList(listId)
    set((state) => {
      const lists = state.lists.filter((l) => l.id !== listId)
      const activeListId = state.activeListId === listId ? null : state.activeListId
      return {
        lists,
        activeListId,
        activeListItems: activeListId === null ? [] : state.activeListItems,
        activeListCodes: activeListId === null ? new Set() : state.activeListCodes,
      }
    })
  },

  addStocks: async (listId: number, tsCodes: string[]) => {
    const res = await apiClient.addStocksToList(listId, tsCodes)
    const result = res.data ?? { added: 0, skipped: 0 }

    // 更新列表中股票计数
    set((state) => ({
      lists: state.lists.map((l) =>
        l.id === listId ? { ...l, stock_count: l.stock_count + result.added } : l
      ),
    }))

    // 如果操作的是当前激活列表，刷新成分股
    if (get().activeListId === listId) {
      await get().refreshActiveListItems()
    }

    return result
  },

  removeStocks: async (listId: number, tsCodes: string[]) => {
    const res = await apiClient.removeStocksFromList(listId, tsCodes)
    const result = res.data ?? { removed: 0 }

    // 更新列表中股票计数
    set((state) => ({
      lists: state.lists.map((l) =>
        l.id === listId ? { ...l, stock_count: Math.max(0, l.stock_count - result.removed) } : l
      ),
    }))

    // 如果操作的是当前激活列表，更新本地成分股（不需要重新请求）
    if (get().activeListId === listId) {
      const removedSet = new Set(tsCodes)
      set((state) => {
        const activeListItems = state.activeListItems.filter((i) => !removedSet.has(i.ts_code))
        return {
          activeListItems,
          activeListCodes: new Set(activeListItems.map((i) => i.ts_code)),
        }
      })
    }

    return result
  },

  reset: () => set(initialState),

  isInActiveList: (tsCode: string) => get().activeListCodes.has(tsCode),
}))
