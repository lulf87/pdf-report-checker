import React, { useState } from 'react'
import { Upload, message, Progress } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UploadOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  SecurityScanOutlined,
  FileSearchOutlined,
  NumberOutlined,
  CheckSquareOutlined,
} from '@ant-design/icons'
import { GlowCard } from '../ui'
import './UploadZone.css'

const { Dragger } = Upload

/**
 * 科技感上传区域组件
 * @param {Object} props
 * @param {Function} props.onUpload - 上传成功回调
 * @param {string} props.apiBaseUrl - API 基础 URL
 */
function UploadZone({ onUpload, apiBaseUrl }) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [fileList, setFileList] = useState([])
  const [dragActive, setDragActive] = useState(false)

  const handleUpload = async (file) => {
    setUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)

    // 模拟进度
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval)
          return 90
        }
        return prev + 10
      })
    }, 100)

    try {
      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (!response.ok) {
        throw new Error('上传失败')
      }

      const result = await response.json()

      if (result.success) {
        message.success('文件上传成功')
        onUpload({
          file_id: result.file_id,
          filename: result.filename,
          file_type: result.file_type,
        })
      } else {
        throw new Error(result.message || '上传失败')
      }
    } catch (error) {
      message.error(`上传失败: ${error.message}`)
      setFileList([])
    } finally {
      setTimeout(() => {
        setUploading(false)
        setUploadProgress(0)
      }, 500)
    }

    return false
  }

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.docx',
    fileList,
    beforeUpload: (file) => {
      const isValidType =
        file.type === 'application/pdf' ||
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

      if (!isValidType) {
        const isPdfByName = file.name.toLowerCase().endsWith('.pdf')
        const isDocxByName = file.name.toLowerCase().endsWith('.docx')

        if (!isPdfByName && !isDocxByName) {
          message.error('只支持 PDF 或 DOCX 文件')
          return Upload.LIST_IGNORE
        }
      }

      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        message.error('文件大小不能超过 50MB')
        return Upload.LIST_IGNORE
      }

      handleUpload(file)
      return false
    },
    onChange: (info) => {
      setFileList(info.fileList.slice(-1))
    },
  }

  // 动画配置
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.6,
        ease: [0.34, 1.56, 0.64, 1],
      },
    },
  }

  // 核对内容项
  const checkItems = [
    { icon: <FileSearchOutlined />, text: '首页与第三页关键字段一致性核对' },
    { icon: <SecurityScanOutlined />, text: '样品描述表格字段提取' },
    { icon: <NumberOutlined />, text: '照片页中文标签 OCR 识别' },
    { icon: <CheckSquareOutlined />, text: '表格字段与标签内容比对' },
    { icon: <CheckCircleOutlined />, text: '检验项目逐项核对' },
  ]

  return (
    <motion.div
      className="upload-zone"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* 标题区域 */}
      <motion.div className="upload-zone__header" variants={itemVariants}>
        <h1 className="upload-zone__title">
          <span className="upload-zone__title-glow">报告审核系统</span>
        </h1>
        <p className="upload-zone__subtitle">
          上传检验报告，系统将自动解析并核对文档内容
        </p>
      </motion.div>

      {/* 上传区域 */}
      <motion.div variants={itemVariants}>
        <div
          className={`upload-zone__drop-area ${dragActive ? 'upload-zone__drop-area--active' : ''}`}
          onDragEnter={() => setDragActive(true)}
          onDragLeave={() => setDragActive(false)}
          onDrop={() => setDragActive(false)}
        >
          {/* 装饰性边角 */}
          <div className="upload-zone__corner upload-zone__corner--tl" />
          <div className="upload-zone__corner upload-zone__corner--tr" />
          <div className="upload-zone__corner upload-zone__corner--bl" />
          <div className="upload-zone__corner upload-zone__corner--br" />

          {/* 扫描线效果 */}
          <div className="upload-zone__scanline" />

          <Dragger {...uploadProps} disabled={uploading} className="upload-zone__dragger">
            <AnimatePresence mode="wait">
              {uploading ? (
                <motion.div
                  key="uploading"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="upload-zone__uploading"
                >
                  <motion.div
                    className="upload-zone__upload-icon"
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <CloudUploadOutlined />
                  </motion.div>
                  <div className="upload-zone__progress">
                    <Progress
                      percent={uploadProgress}
                      status="active"
                      strokeColor={{
                        '0%': '#3b82f6',
                        '100%': '#06b6d4',
                      }}
                      trailColor="rgba(59, 130, 246, 0.1)"
                    />
                  </div>
                  <p className="upload-zone__uploading-text">正在上传文件...</p>
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="upload-zone__idle"
                >
                  <motion.div
                    className="upload-zone__icon-wrapper"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <UploadOutlined className="upload-zone__icon" />
                  </motion.div>
                  <h3 className="upload-zone__drop-title">点击或拖拽文件到此处上传</h3>
                  <p className="upload-zone__drop-hint">
                    支持 PDF / DOCX 格式，文件大小不超过 50MB
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </Dragger>
        </div>
      </motion.div>

      {/* 支持的文件类型 */}
      <motion.div className="upload-zone__file-types" variants={itemVariants}>
        <GlowCard glowColor="blue" className="upload-zone__file-card">
          <div className="upload-zone__file-type">
            <div className="upload-zone__file-icon upload-zone__file-icon--pdf">
              <FilePdfOutlined />
            </div>
            <div className="upload-zone__file-info">
              <span className="upload-zone__file-name">PDF 文件</span>
              <span className="upload-zone__file-desc">推荐格式，解析更稳定</span>
            </div>
          </div>
        </GlowCard>

        <GlowCard glowColor="cyan" className="upload-zone__file-card">
          <div className="upload-zone__file-type">
            <div className="upload-zone__file-icon upload-zone__file-icon--docx">
              <FileWordOutlined />
            </div>
            <div className="upload-zone__file-info">
              <span className="upload-zone__file-name">Word 文档</span>
              <span className="upload-zone__file-desc">DOCX 格式，自动转换</span>
            </div>
          </div>
        </GlowCard>
      </motion.div>

      {/* 核对内容说明 */}
      <motion.div variants={itemVariants}>
        <GlowCard glowColor="success" className="upload-zone__check-info">
          <div className="upload-zone__check-header">
            <CheckCircleOutlined className="upload-zone__check-icon" />
            <h4 className="upload-zone__check-title">核对内容</h4>
          </div>
          <ul className="upload-zone__check-list">
            {checkItems.map((item, index) => (
              <motion.li
                key={index}
                className="upload-zone__check-item"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.8 + index * 0.1 }}
              >
                <span className="upload-zone__check-item-icon">{item.icon}</span>
                <span className="upload-zone__check-item-text">{item.text}</span>
              </motion.li>
            ))}
          </ul>
        </GlowCard>
      </motion.div>
    </motion.div>
  )
}

export default UploadZone
