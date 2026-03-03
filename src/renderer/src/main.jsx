import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App-new.jsx'
import './index.css'

// Ant Design 主题配置
const antdTheme = {
  token: {
    // 主色调 - 医疗蓝
    colorPrimary: '#3b82f6',
    colorPrimaryHover: '#2563eb',
    colorPrimaryActive: '#1d4ed8',

    // 功能色
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorInfo: '#6b7280',

    // 中性色
    colorTextBase: '#1e293b',
    colorText: '#1e293b',
    colorTextSecondary: '#64748b',
    colorTextTertiary: '#94a3b8',

    // 背景色
    colorBgBase: '#f1f5f9',
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBgLayout: '#f1f5f9',

    // 边框色
    colorBorder: '#e2e8f0',
    colorBorderSecondary: '#f1f5f9',

    // 圆角
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    borderRadiusXS: 4,

    // 阴影
    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
    boxShadowSecondary: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    boxShadowTertiary: '0 10px 15px -3px rgb(0 0 0 / 0.1)',

    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,

    // 间距
    paddingSM: 12,
    padding: 16,
    paddingLG: 24,
    paddingXL: 32,

    // 控制组件尺寸
    controlHeight: 36,
    controlHeightLG: 44,
    controlHeightSM: 28,
  },
  components: {
    Card: {
      headerBg: '#f8fafc',
      headerFontSize: 16,
      headerHeight: 56,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#1e293b',
      rowHoverBg: '#f1f5f9',
      padding: 16,
    },
    Button: {
      borderRadius: 8,
      paddingInline: 20,
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Input: {
      borderRadius: 8,
    },
    Select: {
      borderRadius: 8,
    },
    Modal: {
      borderRadiusLG: 16,
    },
    Collapse: {
      headerBg: '#f8fafc',
      contentBg: '#ffffff',
    },
    Tooltip: {
      borderRadius: 8,
    },
    Progress: {
      defaultColor: '#3b82f6',
    },
  },
  algorithm: theme.defaultAlgorithm,
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={antdTheme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
