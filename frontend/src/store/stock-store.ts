import { create } from 'zustand'
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

export const useStockStore = create<StockState>((set) => ({
  stocks: [],
  selectedStock: null,
  dailyData: [],
  isLoading: false,
  error: null,

  setStocks: (stocks) => set({ stocks }),
  setSelectedStock: (stock) => set({ selectedStock: stock }),
  setDailyData: (data) => set({ dailyData: data }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
}))
