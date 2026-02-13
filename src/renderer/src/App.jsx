import React, { useState, useEffect } from 'react'
import { Layout, message, ConfigProvider } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import { UploadZone } from './components/upload'
import { CheckResult } from './components/result'
import { ParticleBackground } from './components/ui'
import './App.css'

const { Header, Content, Footer } = Layout

// API基础URL
const API_BASE_URL = 'http://127.0.0.1:8000'

function App() {
  const [currentFile, setCurrentFile] = useState(null)
  const [checkResult, setCheckResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [llmEnabled, setLlmEnabled] = useState(false)

  // 检查后端状态
  useEffect(() => {
    checkBackendStatus()
    const interval = setInterval(checkBackendStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkBackendStatus = async () => {
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
  }

  const handleFileUpload = async (fileInfo) => {
    setCurrentFile(fileInfo)
    setCheckResult(null)
  }

  const handleCheck = async (fileId) => {
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
  }

  const handleReset = () => {
    setCurrentFile(null)
    setCheckResult(null)
  }

  const getStatusConfig = () => {
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
  }

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
    algorithm: undefined, // 使用默认算法，我们通过 CSS 覆盖
  }

  return (
    <ConfigProvider theme={themeConfig}>
      <Layout className="app-layout">
        {/* 粒子背景 */}
        <ParticleBackground />

        {/* 顶部状态栏 */}
        <Header className="app-header">
          <div className="header-content">
            <motion.h1
              className="app-title"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="app-title__glow">报告审核系统</span>
            </motion.h1>
            <motion.div
              className={`status-indicator status-indicator--${statusConfig.className}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <span className="status-indicator__dot" />
              <span className="status-indicator__text">{statusConfig.text}</span>
            </motion.div>
          </div>
        </Header>

        {/* 主内容区域 */}
        <Content className="app-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentFile ? 'result' : 'upload'}
              className="content-wrapper"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
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
                  onLlmToggle={setLlmEnabled}
                  apiBaseUrl={API_BASE_URL}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </Content>

        {/* 底部信息栏 */}
        <Footer className="app-footer">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="footer-text"
          >
            <span className="footer-text__version">v1.0.0</span>
            <span className="footer-text__divider">|</span>
            <span className="footer-text__copyright">报告审核工具</span>
          </motion.span>
        </Footer>
      </Layout>
    </ConfigProvider>
  )
}

export default App
