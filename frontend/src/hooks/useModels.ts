import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useModels(params?: {
  skip?: number
  limit?: number
  model_type?: string
  source?: string
  search?: string
  sort_by?: string
  sort_order?: string
}) {
  return useQuery({
    queryKey: ['models', 'list', params],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE}/api/ml/models`, { params })
      return response.data
    },
    staleTime: 3 * 60 * 1000,
  })
}

export function useModel(modelId: number) {
  return useQuery({
    queryKey: ['models', 'detail', modelId],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE}/api/ml/models/${modelId}`)
      return response.data
    },
    enabled: !!modelId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTrainModel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (config: any) => {
      const response = await axios.post(`${API_BASE}/api/ml/train`, config)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models', 'list'] })
    },
  })
}

export function useDeleteModel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (modelId: number) => {
      const response = await axios.delete(`${API_BASE}/api/ml/models/${modelId}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models', 'list'] })
    },
  })
}

export function usePrediction(modelId: number) {
  return useQuery({
    queryKey: ['models', 'prediction', modelId],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE}/api/ml/models/${modelId}/prediction`)
      return response.data
    },
    enabled: !!modelId,
    staleTime: 10 * 60 * 1000,
  })
}
