/**
 * FileCard - 文件信息卡片组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React from 'react'
import { Button, Dropdown, Space } from 'antd'
import {
  FileTextOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  ClockCircleOutlined,
  FileOutlined,
} from '@ant-design/icons'
import styles from './FileCard.module.css'

/**
 * 文件信息卡片组件
 * @param {Object} props
 * @param {Object} props.fileInfo - 文件信息对象
 * @param {string} props.fileInfo.filename - 文件名
 * @param {string} props.fileInfo.file_type - 文件类型
 * @param {string} [props.checkTime] - 核对时间
 * @param {number} [props.pageCount] - 页数
 * @param {Function} [props.onExport] - 导出回调函数
 */
function FileCard({ fileInfo, checkTime, pageCount, onExport }) {
  const exportMenuItems = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: '导出 PDF 报告',
      onClick: () => onExport?.('pdf'),
    },
    {
      key: 'excel',
      icon: <FileExcelOutlined />,
      label: '导出 Excel 表格',
      onClick: () => onExport?.('excel'),
    },
  ]

  // 格式化时间
  const formatTime = (time) => {
    if (!time) return '--'
    const date = new Date(time)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className={styles.fileCard}>
      <div className={styles.fileCardContent}>
        {/* 左侧：文件信息 */}
        <div className={styles.fileInfo}>
          {/* 文件图标 */}
          <div className={styles.fileIcon}>
            <FileTextOutlined />
          </div>

          {/* 文件详情 */}
          <div className={styles.fileDetails}>
            <h3 className={styles.fileName}>{fileInfo.filename}</h3>
            <div className={styles.fileMeta}>
              <Space size="middle">
                <span className={styles.metaItem}>
                  <FileOutlined className={styles.metaIcon} />
                  <span>{fileInfo.file_type?.toUpperCase() || '未知'}</span>
                </span>
                {pageCount && (
                  <span className={styles.metaItem}>
                    <span className={styles.metaLabel}>页数:</span>
                    <span className={styles.metaValue}>{pageCount}</span>
                  </span>
                )}
                {checkTime && (
                  <span className={styles.metaItem}>
                    <ClockCircleOutlined className={styles.metaIcon} />
                    <span>{formatTime(checkTime)}</span>
                  </span>
                )}
              </Space>
            </div>
          </div>
        </div>

        {/* 右侧：导出按钮 */}
        {onExport && (
          <Dropdown
            menu={{ items: exportMenuItems }}
            placement="bottomRight"
          >
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              className={styles.exportBtn}
            >
              导出报告
            </Button>
          </Dropdown>
        )}
      </div>

      {/* 装饰性扫描线 */}
      <div className={styles.scanline} />
    </div>
  )
}

export default FileCard
