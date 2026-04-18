'use client'

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { syncDashboardApi, type SyncOverviewItem, type CategoryStat } from '@/lib/api/sync-dashboard'
import { CATEGORY_ORDER } from '../components/constants'

export function useSyncConfigData() {
  const [items, setItems] = useState<SyncOverviewItem[]>([])
  const [categories, setCategories] = useState<CategoryStat[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('全部')
  const [searchText, setSearchText] = useState('')

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setIsLoading(true)
    try {
      const cat = selectedCategory === '全部' ? undefined : selectedCategory
      const resp = await syncDashboardApi.getOverview(cat)
      if (resp.code === 200 && resp.data) {
        setItems(resp.data.items)
        setCategories(resp.data.categories)
      }
    } catch {
      if (!silent) toast.error('加载失败')
    } finally {
      if (!silent) setIsLoading(false)
    }
  }, [selectedCategory])

  useEffect(() => { loadData() }, [loadData])

  // 分组
  const filteredItems = items.filter(i => {
    const q = searchText.trim().toLowerCase()
    return !q || i.display_name.toLowerCase().includes(q) || i.table_key.toLowerCase().includes(q)
  })

  const groupedItems = CATEGORY_ORDER.reduce<Record<string, SyncOverviewItem[]>>((acc, cat) => {
    const filtered = filteredItems.filter(i => i.category === cat)
    if (filtered.length > 0) acc[cat] = filtered
    return acc
  }, {})
  filteredItems.forEach(i => {
    if (!groupedItems[i.category]) groupedItems[i.category] = []
    if (!groupedItems[i.category].find(x => x.table_key === i.table_key)) {
      groupedItems[i.category].push(i)
    }
  })

  const categoryOptions = ['全部', ...CATEGORY_ORDER.filter(c => categories.some(cat => cat.name === c))]

  return {
    items,
    setItems,
    categories,
    isLoading,
    selectedCategory,
    setSelectedCategory,
    searchText,
    setSearchText,
    loadData,
    filteredItems,
    groupedItems,
    categoryOptions,
  }
}
