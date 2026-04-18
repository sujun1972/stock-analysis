'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { schedulerApi } from '@/lib/api'
import { toast } from 'sonner'
import type { ScheduledTask } from '../components/constants'

export function useSchedulerData() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string>('全部')

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true)
      const response = await schedulerApi.getScheduledTasks()
      if (response.data) {
        setTasks(response.data)
      }
    } catch (err: any) {
      toast.error('加载失败', {
        description: err.message || '加载定时任务失败'
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  // 各分类任务计数，避免下拉渲染时重复 filter
  const categoryCounts = useMemo(() => {
    const map: Record<string, number> = { '全部': tasks.length }
    for (const t of tasks) {
      const cat = t.category || '其他'
      map[cat] = (map[cat] ?? 0) + 1
    }
    return map
  }, [tasks])

  // 按分类过滤后的任务列表
  const filteredTasks = useMemo(() => {
    if (selectedCategory === '全部') return tasks
    return tasks.filter(t => (t.category || '其他') === selectedCategory)
  }, [tasks, selectedCategory])

  return {
    tasks,
    setTasks,
    loading,
    loadTasks,
    selectedCategory,
    setSelectedCategory,
    categoryCounts,
    filteredTasks,
  }
}
