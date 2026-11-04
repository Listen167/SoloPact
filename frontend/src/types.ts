export interface Evidence {
  page: number
  quote: string
}

export interface DocumentRecord {
  id: string
  filename: string
  document_type: string
  content_type: string | null
  sha256: string
  storage_provider: string
  status: string
  error_message: string | null
  page_count: number | null
  created_at: string
}

export interface Milestone {
  id: string
  sequence: number
  label: string
  amount: string
  due_date: string
  condition: string
  invoice_required: boolean
  status: string
  confidence: string
  evidence_page: number
  evidence_quote: string
  confirmed: boolean
  paid_at: string | null
}

export interface Contract {
  id: string
  document_id: string | null
  contract_number: string
  title: string
  client_name: string
  provider_name: string
  currency: string
  total_amount: string
  effective_date: string | null
  end_date: string | null
  status: string
  extraction_confidence: string
  source_evidence: Evidence
  milestones: Milestone[]
  created_at: string
  updated_at: string
}

export interface AlertRecord {
  id: string
  milestone_id: string
  alert_type: string
  severity: 'high' | 'medium' | 'low'
  title: string
  explanation: string
  evidence: Evidence
  status: string
  created_at: string
  client_name: string
  contract_title: string
  amount: string
  due_date: string
}

export interface DashboardData {
  as_of: string
  metrics: {
    total_receivable: string
    overdue_amount: string
    due_soon_amount: string
    paid_amount: string
    open_alerts: number
    unmatched_transactions: number
  }
  forecast: Array<{ date: string; expected: string; overdue: string }>
  milestones: Array<{
    id: string
    contract_id: string
    contract_title: string
    client_name: string
    label: string
    amount: string
    due_date: string
    status: string
    confirmed: boolean
  }>
  alerts: AlertRecord[]
}

export interface BankTransaction {
  id: string
  transaction_date: string
  amount: string
  direction: string
  counterparty: string
  memo: string
  import_batch: string
  created_at: string
}

export interface MatchRecord {
  id: string
  milestone_id: string
  transaction_id: string
  score: string
  status: string
  reasons: string[]
  amount_difference: string
  confirmed: boolean
  contract_title: string
  milestone_label: string
  transaction_counterparty: string
  transaction_amount: string
}

export interface DraftRecord {
  id: string
  alert_id: string
  tone: string
  channel: string
  subject: string
  body: string
  evidence_summary: string
  reviewed: boolean
  created_at: string
}

export interface HealthData {
  status: string
  database: string
  storage_provider: string
  ocr_provider: string
  model_provider: string
  demo_today: string
}

