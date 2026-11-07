import { api } from './api'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export type SimStatus =
  | 'IN_HQ_STOCK'
  | 'WITH_BRANCH'
  | 'WITH_BA'
  | 'SOLD'
  | 'RETURNED_TO_BRANCH'
  | 'RETURNED_TO_HQ'
  | 'EXPIRED'
export type ReturnStatusValue = 'REQUESTED' | 'COMPLETED'

export interface Branch {
  id: number
  dealer_id: number
  name: string
  type: 'VAN' | 'SHOP'
  id_number: string
  photo_url: string
  created_by_id: number | null
  created_at: string
}

export interface SimCard {
  id: number
  dealer_id: number
  serial_number: string
  stock_batch_id: number
  status: SimStatus
  current_branch_id: number | null
  current_ba_id: number | null
  expiry_date: string | null
  created_at: string
  updated_at: string
}

export interface IntakeResult {
  batch_id: number
  source_reference: string
  inserted_count: number
  duplicate_count: number
  duplicates: string[]
}

export interface ReturnEvent {
  id: number
  dealer_id: number
  sim_card_id: number
  serial_number: string | null
  requested_by_id: number | null
  branch_id: number
  return_date: string
  reason: string | null
  status: ReturnStatusValue
}

export const simStatusLabels: Record<SimStatus, string> = {
  IN_HQ_STOCK: 'In HQ stock',
  WITH_BRANCH: 'With branch',
  WITH_BA: 'With BA',
  SOLD: 'Sold',
  RETURNED_TO_BRANCH: 'Returned to branch',
  RETURNED_TO_HQ: 'Returned to HQ',
  EXPIRED: 'Expired',
}

export function useBranches() {
  return useQuery({
    queryKey: ['branches'],
    queryFn: async () => {
      const { data } = await api.get<Branch[]>('/branches')
      return data
    },
  })
}

export function useSimCards(filter?: { status?: SimStatus; branch_id?: number }) {
  return useQuery({
    queryKey: ['sim-cards', filter?.status ?? 'all', filter?.branch_id ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filter?.status) params.status_filter = filter.status
      if (filter?.branch_id) params.branch_id = String(filter.branch_id)
      const { data } = await api.get<SimCard[]>('/stock/sim-cards', { params })
      return data
    },
  })
}

export function useReturnRequests() {
  return useQuery({
    queryKey: ['return-requests'],
    queryFn: async () => {
      const { data } = await api.get<ReturnEvent[]>('/stock/return-requests')
      return data
    },
  })
}

export function useBoxScanIntake() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      box_barcode: string
      serials?: string[]
      first_serial?: string
      quantity?: number
      expiry_date?: string
    }) => {
      const { data } = await api.post<IntakeResult>('/stock/intake/box-scan', payload)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sim-cards'] }),
  })
}

export async function uploadPickList(
  file: File,
  onProgress: (percent: number) => void,
): Promise<{ task_id: string }> {
  const body = new FormData()
  body.append('file', file)
  const { data } = await api.post<{ task_id: string; file_reference: string }>(
    '/stock/intake/pick-list-pdf',
    body,
    {
      onUploadProgress: (e) => {
        if (e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    },
  )
  return data
}

export async function distributeStock(payload: {
  branch_id: number
  quantity?: number
  serial_numbers?: string[]
}) {
  const { data } = await api.post<SimCard[]>('/stock/distribute', payload)
  return data
}

export async function createReturnRequest(payload: {
  branch_id: number
  serial_numbers: string[]
  reason?: string
}) {
  const { data } = await api.post<ReturnEvent[]>('/stock/return-requests', payload)
  return data
}