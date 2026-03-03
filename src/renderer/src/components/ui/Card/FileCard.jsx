import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { FileText, FileSpreadsheet, X, CheckCircle2 } from 'lucide-react'
import styles from './FileCard.module.css'

/**
 * FileCard - 文件信息卡片
 * @param {Object} props
 * @param {string} props.filename - 文件名
 * @param {string} [props.fileType] - 文件类型 (pdf/docx)
 * @param {number} [props.fileSize] - 文件大小(字节)
 * @param {boolean} [props.uploaded] - 是否已上传
 * @param {number} [props.progress] - 上传进度(0-100)
 * @param {Function} [props.onRemove] - 移除文件回调
 * @param {Function} [props.onClick] - 点击卡片回调
 * @param {string} [props.className] - 额外的类名
 */
function FileCard({
  filename,
  fileType,
  fileSize,
  uploaded = false,
  progress,
  onRemove,
  onClick,
  className,
  ...rest
}) {
  const cardClasses = classNames(
    styles.fileCard,
    {
      [styles['fileCard--uploaded']]: uploaded,
      [styles['fileCard--clickable']]: onClick,
    },
    className
  )

  const getFileIcon = () => {
    const type = fileType?.toLowerCase() || filename?.split('.').pop()?.toLowerCase()
    if (type === 'pdf') {
      return <FileText className={classNames(styles.fileCard__icon, styles['fileCard__icon--pdf'])} />
    }
    if (type === 'docx' || type === 'doc') {
      return <FileText className={classNames(styles.fileCard__icon, styles['fileCard__icon--docx'])} />
    }
    return <FileSpreadsheet className={styles.fileCard__icon} />
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div
      className={cardClasses}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      {...rest}
    >
      <div className={styles.fileCard__content}>
        {getFileIcon()}
        <div className={styles.fileCard__info}>
          <span className={styles.fileCard__name} title={filename}>
            {filename}
          </span>
          {fileSize > 0 && (
            <span className={styles.fileCard__size}>{formatFileSize(fileSize)}</span>
          )}
        </div>
        {uploaded && (
          <CheckCircle2 className={classNames(styles.fileCard__status, styles['fileCard__status--success'])} />
        )}
      </div>

      {progress !== undefined && progress < 100 && (
        <div className={styles.fileCard__progress}>
          <div
            className={styles.fileCard__progressBar}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {onRemove && (
        <button
          className={styles.fileCard__remove}
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              e.stopPropagation()
              onRemove()
            }
          }}
          aria-label={`移除文件 ${filename}`}
          type="button"
        >
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

FileCard.propTypes = {
  filename: PropTypes.string.isRequired,
  fileType: PropTypes.string,
  fileSize: PropTypes.number,
  uploaded: PropTypes.bool,
  progress: PropTypes.number,
  onRemove: PropTypes.func,
  onClick: PropTypes.func,
  className: PropTypes.string,
}

export default FileCard
