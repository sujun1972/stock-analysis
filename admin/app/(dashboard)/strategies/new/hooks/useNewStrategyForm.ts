'use client'

import { useState } from 'react'

export interface NewStrategyFormData {
  name: string
  display_name: string
  class_name: string
  code: string
  source_type: string
  strategy_type: string
  description: string
  category: string
  tags: string
  default_params: string
  user_id: string
}

const INITIAL_FORM_DATA: NewStrategyFormData = {
  name: '',
  display_name: '',
  class_name: '',
  code: '',
  source_type: 'custom',
  strategy_type: 'stock_selection',
  description: '',
  category: '',
  tags: '',
  default_params: '{}',
  user_id: '',
}

export function useNewStrategyForm() {
  const [formData, setFormData] = useState<NewStrategyFormData>(INITIAL_FORM_DATA)

  const updateField = <K extends keyof NewStrategyFormData>(
    field: K,
    value: NewStrategyFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return {
    formData,
    setFormData,
    updateField,
  }
}
