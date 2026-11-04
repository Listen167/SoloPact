import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { App as AntApp, Button, Layout, Menu, Space, Tag, Tooltip, Typography } from 'antd'
import {
  AlertOutlined,
  ApiOutlined,
  DashboardOutlined,
  FileTextOutlined,
  RadarChartOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
} from '@ant-design/icons'
import { api } from './api'
import type { HealthData } from './types'
import DashboardPage from './pages/DashboardPage'
import DocumentsPage from './pages/DocumentsPage'
import ReconciliationPage from './pages/ReconciliationPage'
import AlertsPage from './pages/AlertsPage'

const { Header, Content, Sider } = Layout

function Shell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { message } = AntApp.useApp()
  const [health, setHealth] = useState<HealthData | null>(null)
  const [resetting, setResetting] = useState(false)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/documents')) return '/documents'
    if (location.pathname.startsWith('/reconciliation')) return '/reconciliation'
    if (location.pathname.startsWith('/alerts')) return '/alerts'
    return '/dashboard'
  }, [location.pathname])

  const resetDemo = async () => {
    setResetting(true)
    try {
      await api.resetDemo()
      message.success('演示数据已恢复')
      navigate('/dashboard')
      window.location.reload()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '重置失败')
    } finally {
      setResetting(false)
    }
  }

  return (
    <Layout className="app-layout">
      <Sider width={236} breakpoint="lg" collapsedWidth={72} className="app-sider">
        <div className="brand">
          <span className="brand-mark"><RadarChartOutlined /></span>
          <span className="brand-text">
            <strong>回款雷达</strong>
            <small>Receivables Agent</small>
          </span>
        </div>
        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/dashboard', icon: <DashboardOutlined />, label: '回款驾驶舱' },
            { key: '/documents', icon: <FileTextOutlined />, label: '文档与合同' },
            { key: '/reconciliation', icon: <SwapOutlined />, label: '回款核对' },
            { key: '/alerts', icon: <AlertOutlined />, label: '风险处置' },
          ]}
        />
        <div className="sider-foot">
          <SafetyCertificateOutlined />
          <span>仅提供经营信息辅助</span>
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space size={10}>
            <Typography.Text strong>极光独立顾问工作室</Typography.Text>
            <Tag bordered={false}>演示租户</Tag>
          </Space>
          <Space size={12}>
            <Tooltip title={health ? `存储：${health.storage_provider} · 模型：${health.model_provider}` : '后端连接异常'}>
              <span className={`service-state ${health ? 'online' : 'offline'}`}>
                <ApiOutlined /> {health ? '服务正常' : '服务异常'}
              </span>
            </Tooltip>
            <Tooltip title="恢复比赛演示的初始数据">
              <Button icon={<ReloadOutlined />} loading={resetting} onClick={resetDemo}>重置演示</Button>
            </Tooltip>
          </Space>
        </Header>
        <Content className="app-content">
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/reconciliation" element={<ReconciliationPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default function App() {
  return <Shell />
}

