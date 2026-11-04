import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { App as AntApp, Button, Empty, Segmented, Skeleton, Space, Tag } from 'antd'
import {
  CheckOutlined,
  CopyOutlined,
  DownloadOutlined,
  FileTextOutlined,
  MailOutlined,
  MessageOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { api } from '../api'
import { PageTitle, StatusTag } from '../components'
import { formatCurrency, formatDate } from '../utils'
import type { AlertRecord, DraftRecord } from '../types'

export default function AlertsPage() {
  const { message } = AntApp.useApp()
  const [searchParams] = useSearchParams()
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [selectedId, setSelectedId] = useState(searchParams.get('selected') ?? '')
  const [tone, setTone] = useState('friendly')
  const [channel, setChannel] = useState('email')
  const [draft, setDraft] = useState<DraftRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    let active = true
    api.alerts()
      .then((rows) => {
        if (!active) return
        setAlerts(rows)
        setSelectedId((current) => current || rows[0]?.id || '')
      })
      .catch((error: Error) => message.error(error.message))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [message])

  const selected = useMemo(() => alerts.find((item) => item.id === selectedId) ?? null, [alerts, selectedId])

  const generateDraft = async () => {
    if (!selected) return
    setGenerating(true)
    try {
      const result = await api.createDraft(selected.id, tone, channel)
      setDraft(result)
      message.success('草稿已生成，发送前请人工确认')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const copyDraft = async () => {
    if (!draft) return
    await navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`)
    message.success('草稿已复制')
  }

  const exportDraft = () => {
    if (!draft) return
    const blob = new Blob([`${draft.subject}\n\n${draft.body}\n\n依据：${draft.evidence_summary}`], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '回款提醒草稿.txt'
    link.click()
    URL.revokeObjectURL(url)
  }

  const markReviewed = async () => {
    if (!draft) return
    const result = await api.reviewDraft(draft.id)
    setDraft(result)
    message.success('已记录人工确认，不会自动发送')
  }

  if (loading) return <Skeleton active paragraph={{ rows: 10 }} />

  return (
    <div className="page-container">
      <PageTitle title="风险处置" meta={`${alerts.length} 项开放提醒 · 所有外发内容均需人工确认`} />
      <div className="alerts-workbench">
        <aside className="alert-queue">
          <div className="section-heading"><div><h2>待处理队列</h2><span>高风险优先</span></div></div>
          {alerts.map((alert) => (
            <button className={`alert-queue-item ${selectedId === alert.id ? 'active' : ''}`} key={alert.id} onClick={() => { setSelectedId(alert.id); setDraft(null) }}>
              <span className={`severity-bar ${alert.severity}`} />
              <span className="alert-queue-copy">
                <strong>{alert.title}</strong>
                <span>{alert.client_name}</span>
                <small>{formatCurrency(alert.amount)} · {formatDate(alert.due_date)}</small>
              </span>
              <StatusTag status={alert.alert_type} />
            </button>
          ))}
          {!alerts.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待处理风险" />}
        </aside>

        <section className="alert-detail">
          {selected ? (
            <>
              <div className="alert-detail-head">
                <div><Space><StatusTag status={selected.alert_type} /><Tag color={selected.severity === 'high' ? 'error' : 'warning'}>{selected.severity === 'high' ? '高风险' : selected.severity === 'medium' ? '中风险' : '低风险'}</Tag></Space><h2>{selected.title}</h2><p>{selected.explanation}</p></div>
                <strong className="alert-amount">{formatCurrency(selected.amount)}</strong>
              </div>
              <div className="evidence-block">
                <div><FileTextOutlined /><strong>合同证据 · 第{selected.evidence.page}页</strong></div>
                <blockquote>{selected.evidence.quote}</blockquote>
              </div>

              <div className="draft-controls">
                <div><span>沟通语气</span><Segmented value={tone} onChange={(value) => setTone(String(value))} options={[{ label: '友好', value: 'friendly' }, { label: '明确', value: 'firm' }, { label: '正式', value: 'formal' }]} /></div>
                <div><span>使用渠道</span><Segmented value={channel} onChange={(value) => setChannel(String(value))} options={[{ label: <><MailOutlined /> 邮件</>, value: 'email' }, { label: <><MessageOutlined /> 微信</>, value: 'wechat' }]} /></div>
                <Button type="primary" icon={<RobotOutlined />} loading={generating} onClick={generateDraft}>生成草稿</Button>
              </div>

              {draft && (
                <div className="draft-output">
                  <div className="draft-output-head"><div><Tag color={draft.reviewed ? 'success' : 'warning'}>{draft.reviewed ? '已人工确认' : '待人工确认'}</Tag><strong>{draft.subject}</strong></div><Space><Button icon={<CopyOutlined />} onClick={copyDraft}>复制</Button><Button icon={<DownloadOutlined />} onClick={exportDraft}>导出</Button></Space></div>
                  <pre>{draft.body}</pre>
                  <div className="draft-evidence">生成依据：{draft.evidence_summary}</div>
                  {!draft.reviewed && <Button icon={<CheckOutlined />} onClick={markReviewed}>标记为已审核</Button>}
                </div>
              )}
            </>
          ) : (
            <Empty description="选择一项风险查看详情" />
          )}
        </section>
      </div>
    </div>
  )
}

