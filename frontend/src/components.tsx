import type { ReactNode } from 'react'
import { Tag } from 'antd'

const statusMap: Record<string, { label: string; color: string }> = {
  confirmed: { label: '已确认', color: 'success' },
  needs_review: { label: '待确认', color: 'warning' },
  ready: { label: '已就绪', color: 'success' },
  processing: { label: '处理中', color: 'processing' },
  failed: { label: '处理失败', color: 'error' },
  paid: { label: '已回款', color: 'success' },
  pending: { label: '待回款', color: 'default' },
  auto_matched: { label: '自动匹配', color: 'success' },
  overdue: { label: '已逾期', color: 'error' },
  due_soon: { label: '临近到期', color: 'warning' },
  amount_mismatch: { label: '金额不符', color: 'warning' },
}

export function StatusTag({ status }: { status: string }) {
  const item = statusMap[status] ?? { label: status, color: 'default' }
  return <Tag color={item.color}>{item.label}</Tag>
}

export function PageTitle({ title, meta, action }: { title: string; meta?: string; action?: ReactNode }) {
  return (
    <div className="page-title-row">
      <div>
        <h1>{title}</h1>
        {meta && <p>{meta}</p>}
      </div>
      {action && <div className="page-title-action">{action}</div>}
    </div>
  )
}

