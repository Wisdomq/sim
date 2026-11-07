import { api } from './api'
import { useQuery, useQueryClient } from '@tanstack/react-query'

export type ImportStatus = 'PROCESSING' | 'COMPLETED' | 'FAILED'
export type MatchStatus =
  | 'MATCHED'
  | 'SOLD_NOT_ACTIVATED'
  | 'ACTIVATED_NOT_RECORDED_SOLD'

export interface SafaricomImport {
  id: number
  dealer_id: number
  uploaded_by_id: number | null
  file_reference: string
  report_date: string
  uploaded_at: string
  row_count: number
  status: ImportStatus
}

export interface ReconResult {
  id: number
  safaricom_import_id: number
  total_sold_in_app: number
  total_confirmed_activated_by_safaricom: number
  total_topped_up: number
  total_cumulative_commission: string
  total_fraud_flagged: number
  unmatched_sold_not_in_safaricom_count: number
  unmatched_in_safaricom_not_sold_in_app_count: number
  generated_at: string
}

export interface ReconLine {
  id: number
  reconciliation_result_id: number
  sim_card_id: number | null
  serial_number: string | null
  top_up_date: string | null
  top_up_amount: string | null
  cumulative_commission: string | null
  fraud_flagged: boolean
  fraud_reason: string | null
  match_status: MatchStatus
}

export const matchStatusLabels: Record<MatchStatus, string> = {
  MATCHED: 'Matched',
  SOLD_NOT_ACTIVATED: 'Sold, not activated',
  ACTIVATED_NOT_RECORDED_SOLD: 'Activated, not sold',
}

export function useImports() {
  return useQuery({
    queryKey: ['recon-imports'],
    queryFn: async () => {
      const { data } = await api.get<SafaricomImport[]>('/reconciliation/imports')
      return data
    },
    staleTime: 5_000,
  })
}

export function useImportResult(importId: number | null) {
  return useQuery({
    queryKey: ['recon-result', importId],
    queryFn: async () => {
      const { data } = await api.get<ReconResult>(`/reconciliation/imports/${importId}`)
      return data
    },
    enabled: importId !== null,
    retry: false,
  })
}

export function useImportDetail(importId: number | null, matchStatus?: MatchStatus | null) {
  return useQuery({
    queryKey: ['recon-detail', importId, matchStatus ?? 'all'],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (matchStatus) params.match_status = matchStatus
      const { data } = await api.get<ReconLine[]>(`/reconciliation/imports/${importId}/detail`, {
        params,
      })
      return data
    },
    enabled: importId !== null,
  })
}

export function useActivatedByMonth(month: string | null) {
  return useQuery({
    queryKey: ['recon-activated', month],
    queryFn: async () => {
      const { data } = await api.get<ReconLine[]>('/reconciliation/activated', {
        params: { month: month ?? '', limit: 200 },
      })
      return data
    },
    enabled: month !== null,
  })
}

export async function uploadReconReport(
  file: File,
  reportDate: string,
  onProgress: (percent: number) => void,
): Promise<{ import_id: number; task_id: string }> {
  const body = new FormData()
  body.append('file', file)
  body.append('report_date', reportDate)
  const { data } = await api.post<{ import_id: number; task_id: string; file_reference: string }>(
    '/reconciliation/imports',
    body,
    {
      onUploadProgress: (e) => {
        if (e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    },
  )
  return data
}

export async function pollImport(
  importId: number,
  qc: ReturnType<typeof useQueryClient>,
  onDone: () => void,
): Promise<void> {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    try {
      const { data } = await api.get<SafaricomImport[]>('/reconciliation/imports')
      const found = data.find((imp) => imp.id === importId)
      if (found && found.status !== 'PROCESSING') {
        onDone()
        await qc.invalidateQueries({ queryKey: ['recon-imports'] })
        await qc.invalidateQueries({ queryKey: ['recon-result', importId] })
        await qc.invalidateQueries({ queryKey: ['recon-detail'] })
        return
      }
    } catch {
      // transient failure while processing; keep polling
    }
    void qc.invalidateQueries({ queryKey: ['recon-imports'] })
  }
  onDone()
}