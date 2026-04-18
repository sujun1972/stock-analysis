'use client'

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { configApi } from '@/lib/api'
import { useConfigStore } from '@/stores/config-store'

export function useGlobalConfig() {
  const { dataSource: configData, fetchDataSourceConfig } = useConfigStore()
  const [globalConfigOpen, setGlobalConfigOpen] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [earliestDate, setEarliestDate] = useState('2021-01-04')
  const [maxRpmInput, setMaxRpmInput] = useState('0')
  const [isSavingGlobal, setIsSavingGlobal] = useState(false)

  useEffect(() => {
    if (globalConfigOpen) {
      fetchDataSourceConfig()
      setTokenInput('')
      setEarliestDate(configData?.earliest_history_date || '2021-01-04')
      setMaxRpmInput(String(configData?.max_requests_per_minute ?? 0))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalConfigOpen])

  useEffect(() => {
    if (configData && globalConfigOpen) {
      setEarliestDate(configData.earliest_history_date || '2021-01-04')
      setMaxRpmInput(String(configData.max_requests_per_minute ?? 0))
    }
  }, [configData, globalConfigOpen])

  const handleSaveGlobal = async () => {
    setIsSavingGlobal(true)
    try {
      const tokenToSave = tokenInput.trim() ? tokenInput.trim() : undefined
      const maxRpm = parseInt(maxRpmInput, 10)
      await configApi.updateDataSourceConfig({
        tushare_token: tokenToSave,
        earliest_history_date: earliestDate || undefined,
        max_requests_per_minute: isNaN(maxRpm) ? 0 : maxRpm,
      })
      fetchDataSourceConfig(true)
      toast.success('配置已保存')
      setGlobalConfigOpen(false)
    } catch (err: any) {
      toast.error(err.message || '保存配置失败')
    } finally {
      setIsSavingGlobal(false)
    }
  }

  return {
    configData,
    globalConfigOpen,
    setGlobalConfigOpen,
    tokenInput,
    setTokenInput,
    earliestDate,
    setEarliestDate,
    maxRpmInput,
    setMaxRpmInput,
    isSavingGlobal,
    handleSaveGlobal,
  }
}
