import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App as AntApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import App from './App'
import './styles.css'

dayjs.locale('zh-cn')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1f6b4f',
          colorInfo: '#2563a6',
          colorSuccess: '#257a55',
          colorWarning: '#b46a14',
          colorError: '#b43a42',
          colorText: '#1d2924',
          colorTextSecondary: '#617068',
          colorBgLayout: '#f4f6f4',
          borderRadius: 6,
          borderRadiusLG: 8,
          fontFamily: "Inter, 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif",
        },
        components: {
          Button: { controlHeight: 36 },
          Table: { headerBg: '#f2f5f3', headerColor: '#405048' },
          Menu: { itemBorderRadius: 5 },
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
)

