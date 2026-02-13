import React, { useState, useEffect } from 'react'
import { Layout, message } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import FileUpload from './components/FileUpload'
import CheckResult from './components/check-result'
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
        return { text: '后端已连接', className: 'connected' }
      case 'disconnected':
        return { text: '后端未连接', className: 'disconnected' }
      case 'error':
        return { text: '后端异常', className: 'error' }
      default:
        return { text: '检查中...', className: 'checking' }
    }
  }

  const statusConfig = getStatusConfig()

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <motion.h1
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            报告审核工具
          </motion.h1>
          <motion.div
            className={`status-indicator ${statusConfig.className}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <span>{statusConfig.text}</span>
          </motion.div>
        </div>
      </Header>

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
              <FileUpload onUpload={handleFileUpload} apiBaseUrl={API_BASE_URL} />
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

      <Footer className="app-footer">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          报告审核工具 v1.0.0
        </motion.span>
      </Footer>
    </Layout>
  )
}

export default App
