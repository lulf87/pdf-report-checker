import React, { useState } from 'react'
import { Upload, Button, Card, message, Space, Typography } from 'antd'
import { UploadOutlined, FilePdfOutlined, FileWordOutlined } from '@ant-design/icons'

const { Title, Text } = Typography
const { Dragger } = Upload

function FileUpload({ onUpload, apiBaseUrl }) {
  const [uploading, setUploading] = useState(false)
  const [fileList, setFileList] = useState([])

  const handleUpload = async (file) => {
    setUploading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      })

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
    } finally {
      setUploading(false)
    }

    return false // 阻止默认上传行为
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

  return (
    <div className="file-upload">
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={3}>上传检验报告</Title>
          <Text type="secondary">
            支持 PDF 或 DOCX 格式的检验报告文件
          </Text>
        </div>

        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
          <p className="ant-upload-hint">
            支持单个文件上传，文件大小不超过 50MB
          </p>
        </Dragger>

        <div style={{ marginTop: 24 }}>
          <Title level={5}>支持的文件类型</Title>
          <Space size="large">
            <Card size="small" style={{ width: 200, textAlign: 'center' }}>
              <FilePdfOutlined style={{ fontSize: 32, color: '#ff4d4f', marginBottom: 8 }} />
              <div>PDF 文件</div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                推荐格式，解析更稳定
              </Text>
            </Card>
            <Card size="small" style={{ width: 200, textAlign: 'center' }}>
              <FileWordOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 8 }} />
              <div>Word 文档</div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                DOCX 格式，将自动转换
              </Text>
            </Card>
          </Space>
        </div>

        <div style={{ marginTop: 24, padding: 16, background: '#f6ffed', borderRadius: 4 }}>
          <Title level={5} style={{ color: '#52c41a' }}>核对内容说明</Title>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>首页与第三页关键字段一致性核对</li>
            <li>样品描述表格字段提取</li>
            <li>照片页中文标签 OCR 识别</li>
            <li>表格字段与标签内容比对</li>
            <li>照片覆盖性检查</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}

export default FileUpload
