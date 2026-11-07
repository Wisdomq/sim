import { api } from './api'
import { type Branch } from './stock'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export type BranchType = 'VAN' | 'SHOP'

export interface BrandAmbassador {
  id: number
  dealer_id: number
  branch_id: number
  user_id: number
  name: string
  phone_msisdn: string | null
  id_number: string
  photo_url: string
  status: 'ACTIVE' | 'DISABLED' | 'FLAGGED_INACTIVE'
  created_by_id: number | null
  created_at: string
}

export interface AccountFlag {
  id: number
  dealer_id: number
  user_id: number
  role: 'HQ' | 'BRANCH' | 'BA'
  flag_type: 'INACTIVE_3_DAYS'
  flagged_at: string
  resolved_at: string | null
  acknowledged_by_id: number | null
  last_login_at: string | null
}

export interface Notification {
  id: number
  dealer_id: number
  user_id: number
  type: string
  title: string
  body: string | null
  metadata_json: Record<string, unknown> | null
  is_read: boolean
  created_at: string
}

export interface CommissionRule {
  id: number
  dealer_id: number
  name: string
  amount_per_sim: string
  effective_from: string
  effective_to: string | null
  created_by_id: number | null
  created_at: string
}

export interface Target {
  id: number
  dealer_id: number
  branch_id: number
  period_type: string
  quantity: number
  effective_from: string
  effective_to: string | null
  set_by_id: number | null
  created_at: string
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

export function useBrandAmbassadors(branchId?: number | null) {
  return useQuery({
    queryKey: ['brand-ambassadors', branchId ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (branchId) params.branch_id = String(branchId)
      const { data } = await api.get<BrandAmbassador[]>('/brand-ambassadors', { params })
      return data
    },
  })
}

export function useFlags(filter?: { resolved?: boolean }) {
  return useQuery({
    queryKey: ['flags', filter?.resolved ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filter?.resolved !== undefined) params.resolved = String(filter.resolved)
      const { data } = await api.get<AccountFlag[]>('/flags', { params })
      return data
    },
  })
}

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const { data } = await api.get<Notification[]>('/flags/notifications')
      return data
    },
    staleTime: 10_000,
  })
}

export function useCommissionRules() {
  return useQuery({
    queryKey: ['commission-rules'],
    queryFn: async () => {
      const { data } = await api.get<CommissionRule[]>('/commission/rules')
      return data
    },
  })
}

export function useTargets() {
  return useQuery({
    queryKey: ['commission-targets'],
    queryFn: async () => {
      const { data } = await api.get<Target[]>('/commission/targets')
      return data
    },
  })
}

export async function uploadPhoto(file: File): Promise<{ photo_url: string; file_reference: string }> {
  const body = new FormData()
  body.append('file', file)
  const { data } = await api.post<{ photo_url: string; file_reference: string }>(
    '/uploads/photo',
    body,
  )
  return data
}

export function useCreateBranch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      name: string
      type: BranchType
      id_number: string
      photo_url: string
      email: string
      password: string
    }) => {
      const { data } = await api.post<Branch>('/branches', payload)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['branches'] }),
  })
}

export function useDeleteBranch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/branches/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['branches'] }),
  })
}

export function useCreateBA() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      branchId: number
      name: string
      email: string
      password: string
      phone_msisdn?: string
      id_number: string
      photo_url: string
    }) => {
      const { data } = await api.post<BrandAmbassador>(
        `/branches/${payload.branchId}/brand-ambassadors`,
        {
          name: payload.name,
          email: payload.email,
          password: payload.password,
          phone_msisdn: payload.phone_msisdn,
          id_number: payload.id_number,
          photo_url: payload.photo_url,
        },
      )
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brand-ambassadors'] }),
  })
}

export function useDeleteBA() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/brand-ambassadors/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['brand-ambassadors'] }),
  })
}

export function useCreateCommissionRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      name: string
      amount_per_sim: string
      effective_from: string
      effective_to?: string
    }) => {
      const { data } = await api.post<CommissionRule>('/commission/rules', {
        name: payload.name,
        amount_per_sim: payload.amount_per_sim,
        effective_from: payload.effective_from,
        effective_to: payload.effective_to ?? null,
      })
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['commission-rules'] }),
  })
}

export function useCreateTarget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      branch_id: number
      period_type: string
      quantity: number
      effective_from: string
      effective_to?: string
    }) => {
      const { data } = await api.post<Target>('/commission/targets', {
        ...payload,
        effective_to: payload.effective_to ?? null,
      })
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['commission-targets'] }),
  })
}

export function useFlagActions() {
  const qc = useQueryClient()
  const base = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: 'acknowledge' }) => {
      const { data } = await api.post<AccountFlag>(`/flags/${id}/${action}`)
      return data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['flags'] })
      void qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
  return base
}

export function useMarkNotificationRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<Notification>(`/flags/notifications/${id}/read`)
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

export function toLocalIso(datetimeLocal: string): string {
  if (!datetimeLocal) return ''
  return new Date(datetimeLocal).toISOString()
}