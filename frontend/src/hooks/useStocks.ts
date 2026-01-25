import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export function useStockList(params?: {
  market?: string
  status?: string
  skip?: number
  limit?: number
  search?: string
  sort_by?: string
  sort_order?: string
}) {
  return useQuery({
    queryKey: ['stocks', 'list', params],
    queryFn: () => apiClient.getStockList(params),
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  })
}

export function useStock(code: string) {
  return useQuery({
    queryKey: ['stocks', 'detail', code],
    queryFn: () => apiClient.getStock(code),
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDailyData(
  code: string,
  params?: { start_date?: string; end_date?: string }
) {
  return useQuery({
    queryKey: ['stocks', 'daily', code, params],
    queryFn: () => apiClient.getDailyData(code, params),
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  })
}

export function useUpdateStockList() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => apiClient.updateStockList(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stocks', 'list'] })
    },
  })
}

export function useSyncRealtimeQuotes() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params?: {
      codes?: string[]
      batch_size?: number
      update_oldest?: boolean
    }) => apiClient.syncRealtimeQuotes(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stocks'] })
    },
  })
}
