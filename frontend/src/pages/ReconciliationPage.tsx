import { useEffect, useMemo, useState } from 'react'
import { App as AntApp, Button, Progress, Space, Table, Tag, Upload } from 'antd'
import type { UploadProps } from 'antd'
import {
  BankOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  SwapOutlined,
} from '@ant-design/icons'
import { api } from '../api'
import { PageTitle, StatusTag } from '../components'
import { formatCurrency, formatDate } from '../utils'
import type { BankTransaction, MatchRecord } from '../types'

export default function ReconciliationPage() {
  const { message } = AntApp.useApp()
  const [matches, setMatches] = useState<MatchRecord[]>([])
  const [transactions, setTransactions] = useState<BankTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [matchRows, transactionRows] = await Promise.all([api.matches(), api.transactions()])
      setMatches(matchRows)
      setTransactions(transactionRows)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([api.matches(), api.transactions()])
      .then(([matchRows, transactionRows]) => {
        if (!active) return
        setMatches(matchRows)
        setTransactions(transactionRows)
      })
      .catch((error: Error) => message.error(error.message))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [message])

  const uploadRequest: NonNullable<UploadProps['customRequest']> = async ({ file, onSuccess, onError }) => {
    try {
      const result = await api.importBank(file as File)
      onSuccess?.(result)
      message.success(`导入${result.imported}条流水，跳过${result.skipped_duplicates}条重复记录`)
      if (result.errors.length) message.warning(`${result.errors.length}行数据需要检查`)
      await load()
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error('导入失败'))
      message.error(error instanceof Error ? error.message : '导入失败')
    }
  }

  const reconcile = async () => {
    setRunning(true)
    try {
      const result = await api.reconcile()
      message.success(`自动匹配${result.auto_matched}项，${result.needs_review}项需要复核`)
      await load()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '核对失败')
    } finally {
      setRunning(false)
    }
  }

  const matchedTransactionIds = useMemo(() => new Set(matches.map((item) => item.transaction_id)), [matches])
  const unmatched = transactions.filter((item) => item.direction === 'inflow' && !matchedTransactionIds.has(item.id))
  const autoMatched = matches.filter((item) => item.status === 'auto_matched').length
  const needsReview = matches.filter((item) => item.status === 'needs_review').length

  return (
    <div className="page-container">
      <PageTitle
        title="回款核对"
        meta="匹配由金额、客户、日期与合同编号规则共同决定"
        action={
          <Space>
            <Upload accept=".csv,.xlsx" showUploadList={false} customRequest={uploadRequest}>
              <Button icon={<CloudUploadOutlined />}>导入流水</Button>
            </Upload>
            <Button type="primary" icon={<PlayCircleOutlined />} loading={running} onClick={reconcile}>运行核对</Button>
          </Space>
        }
      />

      <section className="reconciliation-summary">
        <div><span className="summary-icon success"><CheckCircleOutlined /></span><span>自动确认</span><strong>{autoMatched}</strong></div>
        <div><span className="summary-icon warning"><QuestionCircleOutlined /></span><span>需要复核</span><strong>{needsReview}</strong></div>
        <div><span className="summary-icon neutral"><BankOutlined /></span><span>未关联入账</span><strong>{unmatched.length}</strong></div>
        <div className="rule-note"><SwapOutlined /><span>金额不完全一致的候选项最高只能进入人工复核，不会自动核销。</span></div>
      </section>

      <section className="surface table-surface">
        <div className="section-heading"><div><h2>匹配结果</h2><span>每个结论均展示评分依据</span></div></div>
        <Table
          loading={loading}
          rowKey="id"
          pagination={false}
          scroll={{ x: 920 }}
          dataSource={matches}
          columns={[
            {
              title: '合同付款节点', key: 'milestone', minWidth: 220,
              render: (_, row) => <div className="table-primary"><strong>{row.contract_title}</strong><span>{row.milestone_label}</span></div>,
            },
            {
              title: '入账流水', key: 'transaction', minWidth: 210,
              render: (_, row) => <div className="table-primary"><strong>{row.transaction_counterparty}</strong><span>{formatCurrency(row.transaction_amount)}</span></div>,
            },
            {
              title: '匹配依据', dataIndex: 'reasons', minWidth: 280,
              render: (reasons: string[]) => <Space size={[4, 4]} wrap>{reasons.map((item) => <Tag key={item}>{item}</Tag>)}</Space>,
            },
            {
              title: '置信度', dataIndex: 'score', width: 150,
              render: (value: string) => <Progress percent={Math.round(Number(value) * 100)} size="small" strokeColor={Number(value) >= 0.8 ? '#2b7a5b' : '#b46a14'} />,
            },
            { title: '状态', dataIndex: 'status', width: 120, render: (value: string) => <StatusTag status={value} /> },
          ]}
        />
      </section>

      <section className="surface table-surface">
        <div className="section-heading"><div><h2>银行流水</h2><span>仅流入交易参与回款匹配</span></div><Tag>{transactions.length} 条</Tag></div>
        <Table
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          scroll={{ x: 720 }}
          dataSource={transactions}
          columns={[
            { title: '交易日期', dataIndex: 'transaction_date', width: 120, render: formatDate },
            { title: '交易对手', dataIndex: 'counterparty', width: 220, ellipsis: true },
            { title: '摘要', dataIndex: 'memo', ellipsis: true },
            { title: '方向', dataIndex: 'direction', width: 90, render: (value: string) => <Tag color={value === 'inflow' ? 'success' : 'default'}>{value === 'inflow' ? '流入' : '流出'}</Tag> },
            { title: '金额', dataIndex: 'amount', width: 140, align: 'right', render: formatCurrency },
            { title: '关联', key: 'matched', width: 100, render: (_, row) => matchedTransactionIds.has(row.id) ? <Tag color="success">已关联</Tag> : <Tag>未关联</Tag> },
          ]}
        />
      </section>
    </div>
  )
}

