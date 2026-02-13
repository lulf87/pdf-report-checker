import React, { useState, useEffect, useCallback, memo } from 'react'
import { Layout, message, ConfigProvider } from 'antd'
import { UploadZone } from './components/upload'
import { CheckResult } from './components/result'
import { GridBackground } from './components/ui'
import './App.css'

const { Header, Content, Footer } = Layout

// API基础URL
const API_BASE_URL = 'http://127.0.0.1:8000'

// 状态指示器组件 - 使用CSS动画替代Framer Motion
const StatusIndicator = memo(function StatusIndicator({ statusConfig }) {
  return (
    <div className={`status-indicator status-indicator--${statusConfig.className} fade-in`}>
      <span className="status-indicator__dot" />
      <span className="status-indicator__text">{statusConfig.text}</span>
    </div>
  )
})

// 主标题组件
const AppTitle = memo(function AppTitle() {
  return (
    <h1 className="app-title fade-in">
      <span className="app-title__glow">报告审核系统</span>
    </h1>
  )
})

function App() {
  const [currentFile, setCurrentFile] = useState(null)
  const [checkResult, setCheckResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [llmEnabled, setLlmEnabled] = useState(false)

  // 检查后端状态 - 使用useCallback缓存
  const checkBackendStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      if (response.ok) {
        setBackendStatus('connected')
      } else {
        setBackendStatus('error')
      }
    } catch (error) {
      setBackendStatus('disconnected')
    }
  }, [])

  useEffect(() => {
    checkBackendStatus()
    const interval = setInterval(checkBackendStatus, 5000)
    return () => clearInterval(interval)
  }, [checkBackendStatus])

  const handleFileUpload = useCallback((fileInfo) => {
    setCurrentFile(fileInfo)
    setCheckResult(null)
  }, [])

  const handleCheck = useCallback(async (fileId) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/check/${fileId}?enable_llm=${llmEnabled}&enable_detailed=true`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('核对请求失败')
      }

      const result = await response.json()
      setCheckResult(result)
      message.success('核对完成')
    } catch (error) {
      message.error(`核对失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }, [llmEnabled])

  const handleReset = useCallback(() => {
    setCurrentFile(null)
    setCheckResult(null)
  }, [])

  const handleLlmToggle = useCallback((value) => {
    setLlmEnabled(value)
  }, [])

  const getStatusConfig = useCallback(() => {
    switch (backendStatus) {
      case 'connected':
        return { text: '系统在线', className: 'connected' }
      case 'disconnected':
        return { text: '连接断开', className: 'disconnected' }
      case 'error':
        return { text: '系统异常', className: 'error' }
      default:
        return { text: '检测中...', className: 'checking' }
    }
  }, [backendStatus])

  const statusConfig = getStatusConfig()

  // Ant Design 深色主题配置
  const themeConfig = {
    token: {
      colorPrimary: '#3b82f6',
      colorBgBase: '#111827',
      colorTextBase: '#f9fafb',
      colorBgContainer: 'rgba(17, 24, 39, 0.8)',
      colorBorder: 'rgba(59, 130, 246, 0.2)',
      borderRadius: 8,
    },
    algorithm: undefined,
  }

  return (
    <ConfigProvider theme={themeConfig}>
      <Layout className="app-layout">
        {/* 新UI背景 - 使用GridBackground替代OptimizedBackground */}
        <GridBackground gridSize="md" animated={false} />

        {/* 顶部状态栏 */}
        <Header className="app-header">
          <div className="header-content">
            <AppTitle />
            <StatusIndicator statusConfig={statusConfig} />
          </div>
        </Header>

        {/* 主内容区域 - 使用CSS过渡替代Framer Motion */}
        <Content className="app-content">
          <div
            key={currentFile ? 'result' : 'upload'}
            className="content-wrapper fade-in"
          >
            {!currentFile ? (
              <UploadZone onUpload={handleFileUpload} apiBaseUrl={API_BASE_URL} />
            ) : (
              <CheckResult
                fileInfo={currentFile}
                result={checkResult}
                loading={loading}
                onCheck={() => handleCheck(currentFile.file_id)}
                onReset={handleReset}
                llmEnabled={llmEnabled}
                onLlmToggle={handleLlmToggle}
                apiBaseUrl={API_BASE_URL}
              />
            )}
          </div>
        </Content>

        {/* 底部信息栏 */}
        <Footer className="app-footer">
          <span className="footer-text fade-in">
            <span className="footer-text__version">v1.0.0</span>
            <span className="footer-text__divider">|</span>
            <span className="footer-text__copyright">报告审核工具</span>
          </span>
        </Footer>
      </Layout>
    </ConfigProvider>
  )
}

export default App
