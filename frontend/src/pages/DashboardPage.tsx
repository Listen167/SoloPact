import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Empty, Skeleton, Table, Tag } from 'antd'
import {
  AlertOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { api } from '../api'
import { PageTitle, StatusTag } from '../components'
import { formatCurrency, formatDate } from '../utils'
import type { DashboardData } from '../types'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.dashboard().then(setData).catch((reason: Error) => setError(reason.message))
  }, [])

  const chartOption = useMemo(() => ({
    animationDuration: 500,
    tooltip: { trigger: 'axis', valueFormatter: (value: number) => formatCurrency(value) },
    legend: { top: 0, right: 0, itemWidth: 10, textStyle: { color: '#617068' } },
    grid: { top: 42, left: 10, right: 12, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: data?.forecast.map((item) => dayjs(item.date).format('MM/DD')) ?? [],
      axisLine: { lineStyle: { color: '#d9dfdb' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (value: number) => `${value / 10000}万` },
      splitLine: { lineStyle: { color: '#edf0ee' } },
    },
    series: [
      {
        name: '计划回款',
        type: 'bar',
        stack: 'receivable',
        barMaxWidth: 34,
        itemStyle: { color: '#2b7a5b', borderRadius: [3, 3, 0, 0] },
        data: data?.forecast.map((item) => Number(item.expected)) ?? [],
      },
      {
        name: '已逾期',
        type: 'bar',
        stack: 'receivable',
        barMaxWidth: 34,
        itemStyle: { color: '#c74850', borderRadius: [3, 3, 0, 0] },
        data: data?.forecast.map((item) => Number(item.overdue)) ?? [],
      },
    ],
  }), [data])

  if (error) return <Alert type="error" showIcon message="无法加载驾驶舱" description={error} />
  if (!data) return <Skeleton active paragraph={{ rows: 10 }} />

  const metrics = [
    { label: '待回款总额', value: formatCurrency(data.metrics.total_receivable), icon: <WalletOutlined />, tone: 'neutral' },
    { label: '已逾期', value: formatCurrency(data.metrics.overdue_amount), icon: <AlertOutlined />, tone: 'danger' },
    { label: '14天内到期', value: formatCurrency(data.metrics.due_soon_amount), icon: <ClockCircleOutlined />, tone: 'warning' },
    { label: '已核销回款', value: formatCurrency(data.metrics.paid_amount), icon: <CheckCircleOutlined />, tone: 'success' },
  ]

  return (
    <div className="page-container">
      <PageTitle title="回款驾驶舱" meta={`数据基准日 ${data.as_of} · ${data.metrics.open_alerts} 项待处理风险`} />
      <section className="metric-strip" aria-label="核心回款指标">
        {metrics.map((item) => (
          <div className={`metric-cell ${item.tone}`} key={item.label}>
            <span className="metric-icon">{item.icon}</span>
            <div><span>{item.label}</span><strong>{item.value}</strong></div>
          </div>
        ))}
      </section>

      <div className="dashboard-grid">
        <section className="surface chart-surface">
          <div className="section-heading">
            <div><h2>未来回款节奏</h2><span>按合同付款节点汇总</span></div>
            <Tag bordered={false}>{data.forecast.length} 个节点</Tag>
          </div>
          <ReactECharts option={chartOption} style={{ height: 286 }} />
        </section>
        <section className="surface risk-panel">
          <div className="section-heading">
            <div><h2>优先处理</h2><span>按风险等级排序</span></div>
            <Button type="link" onClick={() => navigate('/alerts')}>全部 <ArrowRightOutlined /></Button>
          </div>
          <div className="risk-list">
            {data.alerts.slice(0, 4).map((alert) => (
              <button className="risk-row" key={alert.id} onClick={() => navigate(`/alerts?selected=${alert.id}`)}>
                <span className={`risk-dot ${alert.severity}`} />
                <span className="risk-copy"><strong>{alert.title}</strong><small>{formatCurrency(alert.amount)} · {formatDate(alert.due_date)}</small></span>
                <ArrowRightOutlined />
              </button>
            ))}
            {!data.alerts.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无风险" />}
          </div>
        </section>
      </div>

      <section className="surface table-surface">
        <div className="section-heading"><div><h2>付款节点</h2><span>合同计划与核销状态</span></div></div>
        <Table
          rowKey="id"
          pagination={false}
          scroll={{ x: 760 }}
          dataSource={data.milestones}
          columns={[
            { title: '客户', dataIndex: 'client_name', width: 180, ellipsis: true },
            { title: '合同', dataIndex: 'contract_title', ellipsis: true },
            { title: '节点', dataIndex: 'label', width: 110 },
            { title: '计划日期', dataIndex: 'due_date', width: 120, render: formatDate },
            { title: '金额', dataIndex: 'amount', width: 140, align: 'right', render: formatCurrency },
            {
              title: '状态', dataIndex: 'status', width: 110,
              render: (value: string, row) => {
                const status = value !== 'paid' && dayjs(row.due_date).isBefore(dayjs(data.as_of), 'day') ? 'overdue' : value
                return <StatusTag status={status} />
              },
            },
          ]}
        />
      </section>
    </div>
  )
}

