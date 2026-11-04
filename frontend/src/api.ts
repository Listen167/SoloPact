import type {
  AlertRecord,
  BankTransaction,
  Contract,
  DashboardData,
  DocumentRecord,
  DraftRecord,
  HealthData,
  MatchRecord,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-Tenant-ID': 'demo',
      ...options?.headers,
    },
  })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const data = (await response.json()) as { detail?: string }
      message = data.detail ?? message
    } catch {
      // Keep the HTTP fallback message.
    }
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<HealthData>('/health'),
  dashboard: () => request<DashboardData>('/dashboard'),
  documents: () => request<DocumentRecord[]>('/documents'),
  contracts: () => request<Contract[]>('/contracts'),
  alerts: () => request<AlertRecord[]>('/alerts'),
  transactions: () => request<BankTransaction[]>('/bank-transactions'),
  matches: () => request<MatchRecord[]>('/reconciliation-matches'),
  resetDemo: () => request<void>('/demo/reset', { method: 'POST' }),
  uploadDocument: async (file: File, documentType: string) => {
    const body = new FormData()
    body.append('file', file)
    body.append('document_type', documentType)
    return request<{ document: DocumentRecord; contract: Contract | null }>('/documents', {
      method: 'POST',
      body,
    })
  },
  reviewContract: (id: string, body: unknown) =>
    request<Contract>(`/contracts/${id}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  importBank: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<{ batch_id: string; imported: number; skipped_duplicates: number; errors: string[] }>(
      '/bank-imports',
      { method: 'POST', body },
    )
  },
  reconcile: () =>
    request<{ auto_matched: number; needs_review: number; unmatched: number; matches: MatchRecord[] }>(
      '/reconciliation-runs',
      { method: 'POST' },
    ),
  createDraft: (alertId: string, tone: string, channel: string) =>
    request<DraftRecord>(`/alerts/${alertId}/draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tone, channel }),
    }),
  reviewDraft: (draftId: string) =>
    request<DraftRecord>(`/drafts/${draftId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewed: true }),
    }),
}

