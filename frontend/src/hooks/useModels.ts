import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axiosInstance from '@/lib/api/axios-instance'


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
      const response = await axiosInstance.get(`/api/ml/models`, { params })
      return response.data
    },
    staleTime: 3 * 60 * 1000,
  })
}

export function useModel(modelId: number) {
  return useQuery({
    queryKey: ['models', 'detail', modelId],
    queryFn: async () => {
      const response = await axiosInstance.get(`/api/ml/models/${modelId}`)
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
      const response = await axiosInstance.post(`/api/ml/train`, config)
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
      const response = await axiosInstance.delete(`/api/ml/models/${modelId}`)
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
      const response = await axiosInstance.get(`/api/ml/models/${modelId}/prediction`)
      return response.data
    },
    enabled: !!modelId,
    staleTime: 10 * 60 * 1000,
  })
}
