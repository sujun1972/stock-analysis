/**
 * 登录瞬间触发本地自选股 → 后端默认列表"自选股"合并
 *
 * 共享逻辑：仅在 `isAuthenticated` 由 false → true 转变时执行一次，避免登录态恢复
 * （页面刷新读取 persist storage）误触发；首挂载基线由 `prevAuthRef` 初值锁定。
 *
 * 因 `/stocks`（sonner toast 直调）和 `/analysis`（shadcn `useToast` 包装）使用不同的 toast API，
 * 调用方传入 `onResult` 回调自行渲染提示，hook 不耦合具体 toast 实现。
 *
 * 失败时回滚 `mergedRef` 允许下次重试；后端 `addStocks` 自带去重，重试不会污染列表。
 */

import { useEffect, useRef } from 'react'
import { useStockListStore } from '@/stores/stock-list-store'
import { useLocalWatchlistStore, LOCAL_WATCHLIST_NAME } from '@/stores/local-watchlist-store'

export interface LoginWatchlistSyncSuccess {
  type: 'success'
  listId: number
  listName: string
  total: number
  added: number
  skipped: number
}

export interface LoginWatchlistSyncFailure {
  type: 'error'
  message: string
}

export type LoginWatchlistSyncResult = LoginWatchlistSyncSuccess | LoginWatchlistSyncFailure

export function useLoginWatchlistSync(
  isAuthenticated: boolean,
  onResult?: (result: LoginWatchlistSyncResult) => void,
) {
  const fetchLists = useStockListStore((s) => s.fetchLists)
  const createList = useStockListStore((s) => s.createList)
  const addStocks = useStockListStore((s) => s.addStocks)
  const localWatchlistClear = useLocalWatchlistStore((s) => s.clear)

  const prevAuthRef = useRef<boolean>(isAuthenticated)
  const mergedRef = useRef<boolean>(false)

  useEffect(() => {
    const prev = prevAuthRef.current
    prevAuthRef.current = isAuthenticated
    if (mergedRef.current) return
    if (!(prev === false && isAuthenticated === true)) return
    const codes = useLocalWatchlistStore.getState().codes
    if (codes.length === 0) return
    mergedRef.current = true
    ;(async () => {
      try {
        await fetchLists()
        const currentLists = useStockListStore.getState().lists
        let target = currentLists.find((l) => l.name === LOCAL_WATCHLIST_NAME)
        if (!target) {
          target = await createList(LOCAL_WATCHLIST_NAME, '从本地浏览器同步')
        }
        const result = await addStocks(target.id, codes)
        localWatchlistClear()
        onResult?.({
          type: 'success',
          listId: target.id,
          listName: target.name,
          total: codes.length,
          added: result.added,
          skipped: result.skipped,
        })
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } }; message?: string }
        onResult?.({
          type: 'error',
          message: e?.response?.data?.detail || e?.message || '未知错误',
        })
        mergedRef.current = false
      }
    })()
  }, [isAuthenticated, fetchLists, createList, addStocks, localWatchlistClear, onResult])
}
