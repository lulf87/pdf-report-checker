import React, { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { Upload, FileText, FileSpreadsheet, X, Loader2, CheckCircle2 } from 'lucide-react'
import styles from './UploadZone.module.css'

/**
 * UploadZone - 拖拽上传区域组件
 * @param {Object} props
 * @param {Function} props.onUpload - 上传回调 (files) => void
 * @param {string[]} [props.accept] - 接受的文件类型
 * @param {number} [props.maxSize] - 最大文件大小(MB)
 * @param {boolean} [props.multiple] - 是否允许多选
 * @param {boolean} [props.disabled] - 是否禁用
 * @param {boolean} [props.loading] - 是否加载中
 * @param {number} [props.progress] - 上传进度(0-100)
 * @param {React.ReactNode} [props.title] - 标题
 * @param {React.ReactNode} [props.hint] - 提示文本
 * @param {string} [props.className] - 额外的类名
 */
function UploadZone({
  onUpload,
  accept = ['.pdf', '.docx'],
  maxSize = 50,
  multiple = false,
  disabled = false,
  loading = false,
  progress = 0,
  title = '点击或拖拽文件到此处上传',
  hint,
  className,
  ...rest
}) {
  const [isDragActive, setIsDragActive] = useState(false)
  const [files, setFiles] = useState([])

  const handleDragEnter = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled && !loading) {
      setIsDragActive(true)
    }
  }, [disabled, loading])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const validateFile = (file) => {
    // 检查文件类型
    const fileExt = `.${file.name.split('.').pop().toLowerCase()}`
    if (accept.length > 0 && !accept.includes(fileExt)) {
      return `不支持的文件类型: ${fileExt}`
    }

    // 检查文件大小
    if (maxSize && file.size > maxSize * 1024 * 1024) {
      return `文件大小超过限制: ${maxSize}MB`
    }

    return null
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)

    if (disabled || loading) return

    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = []
    const errors = []

    droppedFiles.forEach((file) => {
      const error = validateFile(file)
      if (error) {
        errors.push(`${file.name}: ${error}`)
      } else {
        validFiles.push(file)
      }
    })

    if (errors.length > 0) {
      console.warn('文件验证失败:', errors)
    }

    if (validFiles.length > 0) {
      if (multiple) {
        setFiles((prev) => [...prev, ...validFiles])
        onUpload?.(validFiles)
      } else {
        setFiles([validFiles[0]])
        onUpload?.([validFiles[0]])
      }
    }
  }, [disabled, loading, accept, maxSize, multiple, onUpload])

  const handleFileSelect = useCallback((e) => {
    const selectedFiles = Array.from(e.target.files)
    if (selectedFiles.length > 0) {
      if (multiple) {
        setFiles((prev) => [...prev, ...selectedFiles])
        onUpload?.(selectedFiles)
      } else {
        setFiles([selectedFiles[0]])
        onUpload?.([selectedFiles[0]])
      }
    }
    e.target.value = ''
  }, [multiple, onUpload])

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase()
    if (ext === 'pdf') {
      return <FileText className={classNames(styles.uploadZone__fileIcon, styles['uploadZone__fileIcon--pdf'])} />
    }
    if (ext === 'docx' || ext === 'doc') {
      return <FileText className={classNames(styles.uploadZone__fileIcon, styles['uploadZone__fileIcon--docx'])} />
    }
    return <FileSpreadsheet className={styles.uploadZone__fileIcon} />
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const zoneClasses = classNames(
    styles.uploadZone,
    {
      [styles['uploadZone--active']]: isDragActive,
      [styles['uploadZone--disabled']]: disabled,
      [styles['uploadZone--loading']]: loading,
    },
    className
  )

  return (
    <div className={styles.uploadZone__wrapper} {...rest}>
      <div
        className={zoneClasses}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* 装饰性边角 */}
        <div className={classNames(styles.uploadZone__corner, styles['uploadZone__corner--tl'])} />
        <div className={classNames(styles.uploadZone__corner, styles['uploadZone__corner--tr'])} />
        <div className={classNames(styles.uploadZone__corner, styles['uploadZone__corner--bl'])} />
        <div className={classNames(styles.uploadZone__corner, styles['uploadZone__corner--br'])} />

        {/* 扫描线效果 */}
        {loading && <div className={styles.uploadZone__scanline} />}

        <input
          type="file"
          accept={accept.join(',')}
          multiple={multiple}
          onChange={handleFileSelect}
          disabled={disabled || loading}
          className={styles.uploadZone__input}
          id="upload-input"
        />

        <label htmlFor="upload-input" className={styles.uploadZone__content}>
          {loading ? (
            <div className={styles.uploadZone__loading}>
              <Loader2 className={styles.uploadZone__spinner} size={48} />
              <div className={styles.uploadZone__progress}>
                <div
                  className={styles.uploadZone__progressBar}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className={styles.uploadZone__loadingText}>正在上传... {progress}%</p>
            </div>
          ) : (
            <>
              <div className={styles.uploadZone__iconWrapper}>
                <Upload size={48} className={styles.uploadZone__icon} />
              </div>
              <h3 className={styles.uploadZone__title}>{title}</h3>
              {hint && <p className={styles.uploadZone__hint}>{hint}</p>}
              <p className={styles.uploadZone__accept}>
                支持格式: {accept.join(', ')} (最大 {maxSize}MB)
              </p>
            </>
          )}
        </label>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && !loading && (
        <div className={styles.uploadZone__fileList}>
          {files.map((file, index) => (
            <div key={index} className={styles.uploadZone__fileItem}>
              {getFileIcon(file.name)}
              <div className={styles.uploadZone__fileInfo}>
                <span className={styles.uploadZone__fileName} title={file.name}>
                  {file.name}
                </span>
                <span className={styles.uploadZone__fileSize}>
                  {formatFileSize(file.size)}
                </span>
              </div>
              <CheckCircle2 className={styles.uploadZone__fileStatus} size={20} />
              <button
                className={styles.uploadZone__fileRemove}
                onClick={() => removeFile(index)}
                aria-label="移除文件"
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

UploadZone.propTypes = {
  onUpload: PropTypes.func,
  accept: PropTypes.arrayOf(PropTypes.string),
  maxSize: PropTypes.number,
  multiple: PropTypes.bool,
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  progress: PropTypes.number,
  title: PropTypes.node,
  hint: PropTypes.node,
  className: PropTypes.string,
}

export default UploadZone
