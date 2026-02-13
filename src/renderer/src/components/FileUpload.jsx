import React, { useState } from 'react'
import { Upload, Button, Card, message, Space, Typography, Progress } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UploadOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  FileOutlined,
  CloseCircleOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography
const { Dragger } = Upload

function FileUpload({ onUpload, apiBaseUrl }) {
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
      setUploadProgress(prev => {
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
      const isValidType = file.type === 'application/pdf' ||
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

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.34, 1.56, 0.64, 1]
      }
    }
  }

  return (
    <motion.div
      className="file-upload"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* 标题区域 */}
      <motion.div
        className="text-center mb-10"
        variants={itemVariants}
      >
        <Title level={2} className="mb-3">
          <span className="text-gradient">上传检验报告</span>
        </Title>
        <Text type="secondary" className="text-base">
          支持 PDF 或 DOCX 格式的检验报告文件，系统将自动解析并核对
        </Text>
      </motion.div>

      {/* 上传区域 - Glassmorphism 效果 */}
      <motion.div
        variants={itemVariants}
        className="mb-8"
      >
        <div
          className={`
            relative overflow-hidden rounded-2xl border-2 border-dashed
            transition-all duration-300 ease-out
            ${dragActive
              ? 'border-medical-500 bg-medical-50/50'
              : 'border-slate-300 bg-white/50 hover:border-medical-400 hover:bg-white/70'
            }
          `}
          onDragEnter={() => setDragActive(true)}
          onDragLeave={() => setDragActive(false)}
          onDrop={() => setDragActive(false)}
        >
          {/* 背景装饰 */}
          <div className="absolute inset-0 bg-gradient-to-br from-medical-50/30 via-transparent to-transparent pointer-events-none" />

          <Dragger
            {...uploadProps}
            disabled={uploading}
            className="bg-transparent border-0 py-12"
          >
            <AnimatePresence mode="wait">
              {uploading ? (
                <motion.div
                  key="uploading"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="py-4"
                >
                  <CloudUploadOutlined className="text-5xl text-medical-500 mb-4" />
                  <div className="max-w-xs mx-auto">
                    <Progress
                      percent={uploadProgress}
                      status="active"
                      strokeColor={{ from: '#3b82f6', to: '#2563eb' }}
                      trailColor="#e2e8f0"
                    />
                  </div>
                  <Text type="secondary" className="mt-2 block">
                    正在上传文件...
                  </Text>
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="py-4"
                >
                  <motion.div
                    className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-medical-100 to-medical-50 mb-4"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <UploadOutlined className="text-3xl text-medical-500" />
                  </motion.div>
                  <Title level={4} className="mb-2">
                    点击或拖拽文件到此处上传
                  </Title>
                  <Paragraph type="secondary" className="mb-0">
                    支持单个文件上传，文件大小不超过 50MB
                  </Paragraph>
                </motion.div>
              )}
            </AnimatePresence>
          </Dragger>
        </div>
      </motion.div>

      {/* 支持的文件类型 */}
      <motion.div variants={itemVariants} className="mb-8">
        <Title level={5} className="mb-4 text-slate-700">支持的文件类型</Title>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <motion.div
            whileHover={{ y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/70 border border-slate-200/60 backdrop-blur-sm"
          >
            <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-red-50 flex items-center justify-center">
              <FilePdfOutlined className="text-2xl text-red-500" />
            </div>
            <div>
              <div className="font-semibold text-slate-800">PDF 文件</div>
              <Text type="secondary" className="text-sm">推荐格式，解析更稳定</Text>
            </div>
          </motion.div>

          <motion.div
            whileHover={{ y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/70 border border-slate-200/60 backdrop-blur-sm"
          >
            <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
              <FileWordOutlined className="text-2xl text-blue-500" />
            </div>
            <div>
              <div className="font-semibold text-slate-800">Word 文档</div>
              <Text type="secondary" className="text-sm">DOCX 格式，将自动转换</Text>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* 核对内容说明 */}
      <motion.div variants={itemVariants}>
        <div className="p-6 rounded-xl bg-gradient-to-r from-emerald-50/80 to-teal-50/80 border border-emerald-100/60 backdrop-blur-sm">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircleOutlined className="text-emerald-500" />
            <Title level={5} className="mb-0 text-emerald-700">核对内容说明</Title>
          </div>
          <ul className="m-0 pl-5 space-y-2 text-slate-600">
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              首页与第三页关键字段一致性核对
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              样品描述表格字段提取
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              照片页中文标签 OCR 识别
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              表格字段与标签内容比对
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              照片覆盖性检查
            </li>
          </ul>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default FileUpload
