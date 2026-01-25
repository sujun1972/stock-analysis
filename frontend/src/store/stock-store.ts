import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { StockInfo, StockDaily } from '@/types'

interface StockState {
  // 股票列表
  stocks: StockInfo[]
  selectedStock: StockInfo | null

  // 日线数据
  dailyData: StockDaily[]

  // 加载状态
  isLoading: boolean
  error: string | null

  // Actions
  setStocks: (stocks: StockInfo[]) => void
  setSelectedStock: (stock: StockInfo | null) => void
  setDailyData: (data: StockDaily[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useStockStore = create<StockState>()(
  devtools(
    persist(
      (set) => ({
        stocks: [],
        selectedStock: null,
        dailyData: [],
        isLoading: false,
        error: null,

        setStocks: (stocks) => set({ stocks }, false, 'stockStore/setStocks'),
        setSelectedStock: (stock) => set({ selectedStock: stock }, false, 'stockStore/setSelectedStock'),
        setDailyData: (data) => set({ dailyData: data }, false, 'stockStore/setDailyData'),
        setLoading: (loading) => set({ isLoading: loading }, false, 'stockStore/setLoading'),
        setError: (error) => set({ error }, false, 'stockStore/setError'),
      }),
      {
        name: 'stock-storage',
        // 仅持久化选中的股票，不持久化列表和加载状态
        partialize: (state) => ({
          selectedStock: state.selectedStock,
        }),
      }
    ),
    { name: 'StockStore' }
  )
)
