import React, { useState, useEffect } from 'react'
import { Layout, message } from 'antd'
import FileUpload from './components/FileUpload'
import CheckResult from './components/CheckResult'
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

  const getStatusText = () => {
    switch (backendStatus) {
      case 'connected':
        return { text: '后端已连接', color: '#52c41a' }
      case 'disconnected':
        return { text: '后端未连接', color: '#ff4d4f' }
      case 'error':
        return { text: '后端异常', color: '#faad14' }
      default:
        return { text: '检查中...', color: '#999' }
    }
  }

  const status = getStatusText()

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <h1>报告审核工具</h1>
          <div className="status-indicator" style={{ color: status.color }}>
            {status.text}
          </div>
        </div>
      </Header>

      <Content className="app-content">
        <div className="content-wrapper">
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
        </div>
      </Content>

      <Footer className="app-footer">
        报告审核工具 v1.0.0
      </Footer>
    </Layout>
  )
}

export default App
