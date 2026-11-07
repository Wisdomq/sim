import { useQuery } from '@tanstack/react-query'
import dayjs, { type Dayjs } from 'dayjs'
import { api } from './api'
import type { ReportRequest, ReportResponse } from '../types/api'

export type PeriodType = 'DAILY' | 'WEEKLY' | 'MONTHLY'

export function periodDefaults(period: PeriodType): { start: string; end: string } {
  const base = dayjs()
  if (period === 'DAILY') {
    return { start: base.format('YYYY-MM-DD'), end: base.format('YYYY-MM-DD') }
  }
  if (period === 'WEEKLY') {
    const day = base.day() === 0 ? 7 : base.day() // Mon=1 … Sun=7
    const monday = base.subtract(day - 1, 'day').startOf('day')
    const sunday = monday.add(6, 'day')
    return { start: monday.format('YYYY-MM-DD'), end: sunday.format('YYYY-MM-DD') }
  }
  return {
    start: base.startOf('month').format('YYYY-MM-DD'),
    end: base.endOf('month').format('YYYY-MM-DD'),
  }
}

export function useReport(period: PeriodType, range: [string, string] | null, branchId?: number | null) {
  const resolved: [string, string] = range ?? (() => {
    const d = periodDefaults(period)
    return [d.start, d.end]
  })()
  const [start, end] = resolved
  return useQuery({
    queryKey: ['report', period, start, end, branchId ?? 'all'],
    queryFn: async () => {
      const payload: ReportRequest = {
        period_type: period,
        period_start: start,
        period_end: end,
        branch_id: branchId ?? null,
      }
      const { data } = await api.post<ReportResponse>('/reports', payload)
      return data
    },
    enabled: !!range,
  })
}

export interface ReportFile {
  filename: string
  file_path: string
  size_bytes: number
  created_at: number
  format: 'PDF' | 'XLSX'
}

export function useReportFiles() {
  return useQuery({
    queryKey: ['report-files'],
    queryFn: async () => {
      const { data } = await api.get<{ reports: ReportFile[] }>('/reports/list')
      return data.reports
    },
    staleTime: 5_000,
  })
}

export async function dispatchExport(
  period: PeriodType,
  start: string,
  end: string,
  format: 'PDF' | 'XLSX',
  branchId?: number | null,
): Promise<{ task_id: string }> {
  const { data } = await api.post<{ task_id: string; status: string }>('/reports/export', {
    period_type: period,
    period_start: start,
    period_end: end,
    branch_id: branchId ?? null,
    export_format: format,
  })
  return data
}

export async function downloadReportFile(file: ReportFile): Promise<void> {
  const { data } = await api.get(`/reports/download/${file.file_path}`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = file.filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function formatMoney(value: unknown): string {
  const n = typeof value === 'string' ? Number(value) : Number(value)
  return `Ksh ${Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}`
}

export function formatPercent(value: unknown): string {
  const n = typeof value === 'string' ? Number(value) : Number(value)
  return Number.isFinite(n) ? `${n.toFixed(1)}%` : '—'
}

export function formatDate(d: string | Dayjs): string {
  return dayjs(d).format('D MMM YYYY')
}