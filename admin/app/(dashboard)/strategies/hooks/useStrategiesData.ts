'use client'

import { useEffect, useState, useCallback } from 'react'
import { Strategy } from '@/types/strategy'
import { axiosInstance } from '@/lib/api'
import logger from '@/lib/logger'
import { toast } from 'sonner'

const PAGE_SIZE = 20

export function useStrategiesData() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStrategyType, setFilterStrategyType] = useState<string>('all')
  const [filterSourceType, setFilterSourceType] = useState<string>('all')
  const [filterUserId, setFilterUserId] = useState<string>('all')
  const [filterPublishStatus, setFilterPublishStatus] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  const fetchStrategies = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {
        page: currentPage,
        page_size: PAGE_SIZE,
      }

      if (searchTerm) params.search = searchTerm
      if (filterStrategyType && filterStrategyType !== 'all') params.strategy_type = filterStrategyType
      if (filterSourceType && filterSourceType !== 'all') params.source_type = filterSourceType
      if (filterUserId && filterUserId !== 'all') params.user_id = filterUserId
      if (filterPublishStatus && filterPublishStatus !== 'all') params.publish_status = filterPublishStatus

      const response = await axiosInstance.get('/api/strategies', { params }) as any

      if (response?.code === 200 && response.data) {
        const { items, total } = response.data
        if (items && Array.isArray(items)) {
          setStrategies(items)
          setTotalCount(total || 0)
        }
      }
    } catch (error) {
      logger.error('获取策略列表失败', error)
      toast.error('获取策略列表失败')
    } finally {
      setLoading(false)
    }
  }, [currentPage, searchTerm, filterStrategyType, filterSourceType, filterUserId, filterPublishStatus])

  useEffect(() => {
    fetchStrategies()
  }, [fetchStrategies])

  const handleResetFilters = () => {
    setSearchTerm('')
    setFilterStrategyType('all')
    setFilterSourceType('all')
    setFilterUserId('all')
    setFilterPublishStatus('all')
    setCurrentPage(1)
  }

  return {
    strategies,
    loading,
    searchTerm,
    setSearchTerm,
    filterStrategyType,
    setFilterStrategyType,
    filterSourceType,
    setFilterSourceType,
    filterUserId,
    setFilterUserId,
    filterPublishStatus,
    setFilterPublishStatus,
    currentPage,
    setCurrentPage,
    totalCount,
    pageSize: PAGE_SIZE,
    fetchStrategies,
    handleResetFilters,
  }
}
