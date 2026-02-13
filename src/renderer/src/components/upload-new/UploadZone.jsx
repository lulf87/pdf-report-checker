import React, { useState, useCallback, useRef } from 'react'
import {
  Upload,
  FileText,
  FileType,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  FileSearch,
  ScanLine,
  ClipboardCheck,
  Hash,
  Image,
  LayoutList,
  Shield
} from 'lucide-react'
import styles from './UploadZone.module.css'

/**
 * 现代化文件上传区域组件
 * @param {Object} props
 * @param {Function} props.onUpload - 上传成功回调
 * @param {string} props.apiBaseUrl - API 基础 URL
 */
function UploadZone({ onUpload, apiBaseUrl }) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedFile, setSelectedFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState(null)
  const [checkInfoExpanded, setCheckInfoExpanded] = useState(true)
  const inputRef = useRef(null)

  // 文件类型验证
  const validateFile = (file) => {
    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    const isDocx = file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                   file.name.toLowerCase().endsWith('.docx')

    if (!isPdf && !isDocx) {
      return { valid: false, message: '只支持 PDF 或 DOCX 文件' }
    }

    const isLt50M = file.size / 1024 / 1024 < 50
    if (!isLt50M) {
      return { valid: false, message: '文件大小不能超过 50MB' }
    }

    return { valid: true }
  }

  // 处理文件选择
  const handleFileSelect = useCallback((file) => {
    setError(null)
    const validation = validateFile(file)

    if (!validation.valid) {
      setError(validation.message)
      return false
    }

    setSelectedFile(file)
    handleUpload(file)
    return true
  }, [])

  // 处理上传
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
        onUpload({
          file_id: result.file_id,
          filename: result.filename,
          file_type: result.file_type,
        })
      } else {
        throw new Error(result.message || '上传失败')
      }
    } catch (err) {
      setError(`上传失败: ${err.message}`)
      setSelectedFile(null)
    } finally {
      setTimeout(() => {
        setUploading(false)
        setUploadProgress(0)
      }, 500)
    }
  }

  // 拖拽事件处理
  const handleDrag = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }, [handleFileSelect])

  // 点击上传
  const handleClick = () => {
    inputRef.current?.click()
  }

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  // 删除已选文件
  const handleRemoveFile = () => {
    setSelectedFile(null)
    setError(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 获取文件图标
  const getFileIcon = (filename) => {
    if (filename.toLowerCase().endsWith('.pdf')) {
      return <FileText className={styles.fileIconPdf} />
    }
    return <FileType className={styles.fileIconDocx} />
  }

  // 核对内容分组数据
  const checkGroups = [
    {
      id: 'basic',
      title: '报告基础核对',
      icon: <FileSearch size={18} />,
      color: 'blue',
      items: [
        { icon: <CheckCircle2 size={14} />, text: 'C01: 首页与第三页关键字段一致性核对' },
        { icon: <CheckCircle2 size={14} />, text: 'C02: 报告编号格式校验' },
      ]
    },
    {
      id: 'sample',
      title: '样品照片核对',
      icon: <Image size={18} />,
      color: 'purple',
      items: [
        { icon: <CheckCircle2 size={14} />, text: 'C03: 样品描述表格字段提取' },
        { icon: <CheckCircle2 size={14} />, text: 'C04: 照片页中文标签 OCR 识别' },
        { icon: <CheckCircle2 size={14} />, text: 'C05: 表格字段与标签内容比对' },
        { icon: <CheckCircle2 size={14} />, text: 'C06: 照片数量与描述一致性' },
      ]
    },
    {
      id: 'inspection',
      title: '检验项目核对',
      icon: <ClipboardCheck size={18} />,
      color: 'green',
      items: [
        { icon: <CheckCircle2 size={14} />, text: 'C07: 检验项目逐项核对' },
        { icon: <CheckCircle2 size={14} />, text: 'C08: 检验结果与结论一致性' },
        { icon: <CheckCircle2 size={14} />, text: 'C09: 标准要求与实测值比对' },
      ]
    },
    {
      id: 'page',
      title: '页码校验',
      icon: <Hash size={18} />,
      color: 'cyan',
      items: [
        { icon: <CheckCircle2 size={14} />, text: 'C10: 页码连续性检查' },
        { icon: <CheckCircle2 size={14} />, text: 'C11: 总页数与目录一致性' },
      ]
    }
  ]

  return (
    <div className={styles.uploadZone}>
      {/* 标题区域 */}
      <div className={styles.header}>
        <h1 className={styles.title}>
          <span className={styles.titleGlow}>报告审核系统</span>
        </h1>
        <p className={styles.subtitle}>
          上传检验报告，系统将自动解析并核对文档内容
        </p>
      </div>

      {/* 上传区域 */}
      <div
        className={`${styles.dropArea} ${dragActive ? styles.dropAreaActive : ''} ${uploading ? styles.dropAreaUploading : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={!uploading && !selectedFile ? handleClick : undefined}
      >
        {/* 装饰性边角 */}
        <div className={`${styles.corner} ${styles.cornerTl}`} />
        <div className={`${styles.corner} ${styles.cornerTr}`} />
        <div className={`${styles.corner} ${styles.cornerBl}`} />
        <div className={`${styles.corner} ${styles.cornerBr}`} />

        {/* 扫描线效果 */}
        {uploading && <div className={styles.scanline} />}

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleInputChange}
          className={styles.hiddenInput}
        />

        {/* 上传状态内容 */}
        {!selectedFile && !uploading && (
          <div className={styles.idleState}>
            <div className={styles.iconWrapper}>
              <Upload size={48} className={styles.uploadIcon} />
            </div>
            <h3 className={styles.dropTitle}>点击或拖拽文件到此处上传</h3>
            <p className={styles.dropHint}>
              支持 PDF / DOCX 格式，文件大小不超过 50MB
            </p>
          </div>
        )}

        {/* 上传中状态 */}
        {uploading && (
          <div className={styles.uploadingState}>
            <div className={styles.uploadingIconWrapper}>
              <Loader2 size={48} className={styles.spinnerIcon} />
            </div>
            <div className={styles.progressContainer}>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <span className={styles.progressText}>{uploadProgress}%</span>
            </div>
            <p className={styles.uploadingText}>正在上传并解析文件...</p>
          </div>
        )}

        {/* 已选文件状态 */}
        {selectedFile && !uploading && (
          <div className={styles.fileState}>
            <div className={styles.fileCard}>
              <div className={styles.fileIconWrapper}>
                {getFileIcon(selectedFile.name)}
              </div>
              <div className={styles.fileInfo}>
                <span className={styles.fileName}>{selectedFile.name}</span>
                <span className={styles.fileSize}>{formatFileSize(selectedFile.size)}</span>
              </div>
              <button
                className={styles.removeButton}
                onClick={(e) => {
                  e.stopPropagation()
                  handleRemoveFile()
                }}
                title="删除文件"
              >
                <X size={18} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className={styles.errorMessage}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* 支持的文件类型 */}
      <div className={styles.fileTypes}>
        <div className={styles.fileTypeCard}>
          <div className={styles.fileTypeIconPdf}>
            <FileText size={24} />
          </div>
          <div className={styles.fileTypeInfo}>
            <span className={styles.fileTypeName}>PDF 文件</span>
            <span className={styles.fileTypeDesc}>推荐格式，解析更稳定</span>
          </div>
        </div>

        <div className={styles.fileTypeCard}>
          <div className={styles.fileTypeIconDocx}>
            <FileType size={24} />
          </div>
          <div className={styles.fileTypeInfo}>
            <span className={styles.fileTypeName}>Word 文档</span>
            <span className={styles.fileTypeDesc}>DOCX 格式，自动转换</span>
          </div>
        </div>
      </div>

      {/* 核对内容说明 */}
      <div className={styles.checkInfo}>
        <div
          className={styles.checkInfoHeader}
          onClick={() => setCheckInfoExpanded(!checkInfoExpanded)}
        >
          <div className={styles.checkInfoTitle}>
            <Shield size={20} className={styles.checkInfoIcon} />
            <h4>核对内容说明</h4>
            <span className={styles.checkInfoBadge}>C01-C11</span>
          </div>
          <button className={styles.expandButton}>
            {checkInfoExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>

        {checkInfoExpanded && (
          <div className={styles.checkGroups}>
            {checkGroups.map((group) => (
              <div key={group.id} className={`${styles.checkGroup} ${styles[`checkGroup${group.color.charAt(0).toUpperCase() + group.color.slice(1)}`]}`}>
                <div className={styles.checkGroupHeader}>
                  <span className={styles.checkGroupIcon}>{group.icon}</span>
                  <span className={styles.checkGroupTitle}>{group.title}</span>
                </div>
                <ul className={styles.checkGroupList}>
                  {group.items.map((item, index) => (
                    <li key={index} className={styles.checkGroupItem}>
                      <span className={styles.checkItemIcon}>{item.icon}</span>
                      <span className={styles.checkItemText}>{item.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default UploadZone
