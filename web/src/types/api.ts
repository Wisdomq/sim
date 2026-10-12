export type Role = 'HQ' | 'BRANCH' | 'BA'
export type AccountStatus = 'ACTIVE' | 'DISABLED' | 'FLAGGED_INACTIVE'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface CurrentUser {
  id: number
  dealer_id: number
  role: Role
  email: string
  branch_id: number | null
  ba_profile_id: number | null
  status: AccountStatus
}

export interface ReportRequest {
  period_type: 'DAILY' | 'WEEKLY' | 'MONTHLY'
  period_start: string
  period_end: string
  branch_id?: number | null
}

export interface StockCountsByStatus {
  in_hq_stock: number
  with_branch: number
  with_ba: number
  sold: number
  returned_to_branch: number
  returned_to_hq: number
  expired: number
}

export interface BASalesSummary {
  ba_id: number
  ba_name: string
  sales_count: number
  commission_owed: string
  performance_percentage: string
}

export interface BranchReportData {
  branch_id: number
  branch_name: string
  stock_counts: StockCountsByStatus
  total_sales_count: number
  total_commission_owed: string
  performance_percentage: string
  ba_summaries: BASalesSummary[]
}

export interface ReconciliationHeadlines {
  total_confirmed_activated_by_safaricom: number
  total_cumulative_commission: string
  total_fraud_flagged: number
  unmatched_sold_not_in_safaricom_count: number
  unmatched_in_safaricom_not_sold_in_app_count: number
}

export interface ReportResponse {
  period_type: 'DAILY' | 'WEEKLY' | 'MONTHLY'
  period_start: string
  period_end: string
  total_stock_counts: StockCountsByStatus
  total_sales_count: number
  total_commission_owed: string
  overall_performance_percentage: string
  branch_reports: BranchReportData[]
  reconciliation_headlines: ReconciliationHeadlines | null
  generated_at: string
}