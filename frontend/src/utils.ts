import dayjs from 'dayjs'

export function formatCurrency(value: string | number | null | undefined): string {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(value: string | null | undefined): string {
  return value ? dayjs(value).format('YYYY-MM-DD') : '-'
}

