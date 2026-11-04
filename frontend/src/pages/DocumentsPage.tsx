import { useEffect, useMemo, useState } from 'react'
import {
  App as AntApp,
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Progress,
  Segmented,
  Table,
  Tag,
  Upload,
} from 'antd'
import type { UploadProps } from 'antd'
import {
  CheckOutlined,
  CloudUploadOutlined,
  FileSearchOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import { api } from '../api'
import { PageTitle, StatusTag } from '../components'
import { formatCurrency, formatDate } from '../utils'
import type { Contract, DocumentRecord, Milestone } from '../types'

const { Dragger } = Upload

type MilestoneEdit = Milestone & { dueDateValue: Dayjs }

export default function DocumentsPage() {
  const { message } = AntApp.useApp()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [documentType, setDocumentType] = useState('contract')
  const [loading, setLoading] = useState(true)
  const [reviewing, setReviewing] = useState<Contract | null>(null)
  const [milestones, setMilestones] = useState<MilestoneEdit[]>([])
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const [contractRows, documentRows] = await Promise.all([api.contracts(), api.documents()])
      setContracts(contractRows)
      setDocuments(documentRows)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([api.contracts(), api.documents()])
      .then(([contractRows, documentRows]) => {
        if (!active) return
        setContracts(contractRows)
        setDocuments(documentRows)
      })
      .catch((error: Error) => message.error(error.message))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [message])

  const openReview = (contract: Contract) => {
    setReviewing(contract)
    form.setFieldsValue({
      client_name: contract.client_name,
      contract_number: contract.contract_number,
      title: contract.title,
      total_amount: Number(contract.total_amount),
      effective_date: contract.effective_date ? dayjs(contract.effective_date) : null,
      end_date: contract.end_date ? dayjs(contract.end_date) : null,
    })
    setMilestones(contract.milestones.map((item) => ({ ...item, dueDateValue: dayjs(item.due_date) })))
  }

  const uploadRequest: NonNullable<UploadProps['customRequest']> = async ({ file, onSuccess, onError }) => {
    try {
      const result = await api.uploadDocument(file as File, documentType)
      onSuccess?.(result)
      message.success(`${(file as File).name} 已完成处理`)
      await load()
      if (result.contract) openReview(result.contract)
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error('上传失败'))
      message.error(error instanceof Error ? error.message : '上传失败')
    }
  }

  const saveReview = async () => {
    if (!reviewing) return
    const values = await form.validateFields()
    setSaving(true)
    try {
      await api.reviewContract(reviewing.id, {
        ...values,
        effective_date: values.effective_date?.format('YYYY-MM-DD') ?? null,
        end_date: values.end_date?.format('YYYY-MM-DD') ?? null,
        confirmed: true,
        milestones: milestones.map((item) => ({
          id: item.id,
          label: item.label,
          amount: Number(item.amount),
          due_date: item.dueDateValue.format('YYYY-MM-DD'),
          condition: item.condition,
          invoice_required: item.invoice_required,
          confirmed: true,
        })),
      })
      message.success('合同与付款节点已确认')
      setReviewing(null)
      await load()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const pendingReview = useMemo(() => contracts.filter((item) => item.status === 'needs_review').length, [contracts])

  return (
    <div className="page-container">
      <PageTitle
        title="文档与合同"
        meta={`${contracts.length} 份合同 · ${pendingReview} 份待人工确认`}
        action={<Tag icon={<FileSearchOutlined />} color={pendingReview ? 'warning' : 'success'}>{pendingReview ? '存在待确认项' : '提取均已确认'}</Tag>}
      />

      <section className="surface upload-surface">
        <div className="upload-options">
          <div><h2>导入业务文档</h2><span>单个文件最大10MB</span></div>
          <Segmented
            value={documentType}
            onChange={(value) => setDocumentType(String(value))}
            options={[
              { label: '合同', value: 'contract' },
              { label: '发票', value: 'invoice' },
              { label: '其他', value: 'other' },
            ]}
          />
        </div>
        <Dragger
          accept={documentType === 'contract' ? '.pdf,.txt,.md' : '.pdf,.png,.jpg,.jpeg'}
          showUploadList={false}
          customRequest={uploadRequest}
          multiple={false}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">拖拽文件到这里，或点击选择</p>
          <p className="ant-upload-hint">合同支持可复制文本的PDF；扫描件在配置华为云OCR后自动识别</p>
        </Dragger>
      </section>

      <section className="surface table-surface">
        <div className="section-heading">
          <div><h2>合同台账</h2><span>抽取结果必须经人工确认后进入回款流程</span></div>
          <Button icon={<CloudUploadOutlined />} onClick={() => document.querySelector<HTMLElement>('.ant-upload')?.click()}>上传合同</Button>
        </div>
        <Table
          loading={loading}
          rowKey="id"
          dataSource={contracts}
          pagination={false}
          scroll={{ x: 860 }}
          columns={[
            {
              title: '合同', dataIndex: 'title', ellipsis: true,
              render: (value: string, row) => <div className="table-primary"><strong>{value}</strong><span>{row.contract_number}</span></div>,
            },
            { title: '客户', dataIndex: 'client_name', width: 190, ellipsis: true },
            { title: '合同金额', dataIndex: 'total_amount', width: 140, align: 'right', render: formatCurrency },
            { title: '付款节点', dataIndex: 'milestones', width: 100, align: 'center', render: (items: Milestone[]) => items.length },
            {
              title: '抽取置信度', dataIndex: 'extraction_confidence', width: 150,
              render: (value: string) => <Progress percent={Math.round(Number(value) * 100)} size="small" strokeColor="#2b7a5b" />,
            },
            { title: '状态', dataIndex: 'status', width: 100, render: (value: string) => <StatusTag status={value} /> },
            { title: '', key: 'action', width: 110, render: (_, row) => <Button type="link" icon={<FileSearchOutlined />} onClick={() => openReview(row)}>核对</Button> },
          ]}
        />
      </section>

      {documents.length > 0 && (
        <section className="compact-log">
          <span>最近上传：</span>
          {documents.slice(0, 3).map((item) => <Tag key={item.id}>{item.filename} · {formatDate(item.created_at)}</Tag>)}
        </section>
      )}

      <Drawer
        title="核对合同提取结果"
        width={800}
        open={Boolean(reviewing)}
        onClose={() => setReviewing(null)}
        extra={<Button type="primary" icon={<CheckOutlined />} loading={saving} onClick={saveReview}>确认进入台账</Button>}
      >
        {reviewing && (
          <>
            <div className="review-banner">
              <FileSearchOutlined />
              <div><strong>整体置信度 {Math.round(Number(reviewing.extraction_confidence) * 100)}%</strong><span>请逐项核对，确认操作会写入审计记录</span></div>
            </div>
            <Form form={form} layout="vertical" requiredMark={false}>
              <div className="form-grid">
                <Form.Item name="client_name" label="客户名称" rules={[{ required: true }]}><Input /></Form.Item>
                <Form.Item name="contract_number" label="合同编号" rules={[{ required: true }]}><Input /></Form.Item>
                <Form.Item name="title" label="合同名称" rules={[{ required: true }]} className="span-2"><Input /></Form.Item>
                <Form.Item name="total_amount" label="合同总额" rules={[{ required: true }]}><InputNumber min={0} precision={2} prefix="¥" style={{ width: '100%' }} /></Form.Item>
                <Form.Item name="effective_date" label="生效日期"><DatePicker style={{ width: '100%' }} /></Form.Item>
                <Form.Item name="end_date" label="结束日期"><DatePicker style={{ width: '100%' }} /></Form.Item>
              </div>
            </Form>
            <div className="section-heading drawer-heading"><div><h2>付款节点</h2><span>金额、日期与原文引用</span></div></div>
            <Table
              rowKey="id"
              pagination={false}
              scroll={{ x: 680 }}
              dataSource={milestones}
              columns={[
                {
                  title: '节点', width: 110,
                  render: (_, row) => <Input value={row.label} onChange={(event) => setMilestones((items) => items.map((item) => item.id === row.id ? { ...item, label: event.target.value } : item))} />,
                },
                {
                  title: '金额', width: 145,
                  render: (_, row) => <InputNumber value={Number(row.amount)} min={0} prefix="¥" style={{ width: '100%' }} onChange={(value) => setMilestones((items) => items.map((item) => item.id === row.id ? { ...item, amount: String(value ?? 0) } : item))} />,
                },
                {
                  title: '到期日', width: 185,
                  render: (_, row) => <DatePicker value={row.dueDateValue} onChange={(value) => value && setMilestones((items) => items.map((item) => item.id === row.id ? { ...item, dueDateValue: value } : item))} />,
                },
                {
                  title: '合同依据',
                  render: (_, row) => <div className="evidence-cell"><Tag>第{row.evidence_page}页</Tag><span>{row.evidence_quote}</span></div>,
                },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

