/**
 * 未登录用户的本地自选股 Store
 *
 * 设计要点：
 * - 仅一个隐式列表（"自选股"），不支持多列表 / 重命名 / 删除列表
 * - 数据存于 localStorage，登录后由 page.tsx 触发合并到后端默认列表
 * - ts_code 全大写、带交易所后缀（如 000001.SZ）；写入时由调用方保证
 * - 上限 500 与后端列表对齐，避免合并时被服务端拒绝
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const MAX_LOCAL_WATCHLIST = 500

interface LocalWatchlistState {
  codes: string[]
}

interface LocalWatchlistActions {
  has: (tsCode: string) => boolean
  add: (tsCodes: string[]) => { added: number; skipped: number; overflow: number }
  remove: (tsCodes: string[]) => { removed: number }
  clear: () => void
}

export type LocalWatchlistStore = LocalWatchlistState & LocalWatchlistActions

export const LOCAL_WATCHLIST_LIST_ID = 'local' as const
export const LOCAL_WATCHLIST_NAME = '自选股'
export const LOCAL_WATCHLIST_MAX = MAX_LOCAL_WATCHLIST

export const useLocalWatchlistStore = create<LocalWatchlistStore>()(
  persist(
    (set, get) => ({
      codes: [],

      has: (tsCode) => get().codes.includes(tsCode),

      add: (tsCodes) => {
        const existing = new Set(get().codes)
        const remaining = MAX_LOCAL_WATCHLIST - existing.size
        let added = 0
        let skipped = 0
        let overflow = 0
        const next = [...get().codes]
        for (const code of tsCodes) {
          if (existing.has(code)) { skipped++; continue }
          if (added >= remaining) { overflow++; continue }
          existing.add(code)
          next.push(code)
          added++
        }
        if (added > 0) set({ codes: next })
        return { added, skipped, overflow }
      },

      remove: (tsCodes) => {
        const removeSet = new Set(tsCodes)
        const before = get().codes
        const next = before.filter((c) => !removeSet.has(c))
        const removed = before.length - next.length
        if (removed > 0) set({ codes: next })
        return { removed }
      },

      clear: () => set({ codes: [] }),
    }),
    {
      name: 'local-watchlist:v1',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ codes: state.codes }),
    }
  )
)
