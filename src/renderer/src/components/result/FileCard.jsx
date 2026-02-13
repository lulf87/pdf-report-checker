import React from 'react'
import { Button, Dropdown, Space } from 'antd'
import { motion } from 'framer-motion'
import {
  FileTextOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  ClockCircleOutlined,
  FileOutlined,
} from '@ant-design/icons'
import { GlowCard } from '../ui'
import './FileCard.module.css'

/**
 * 文件信息卡片组件 - 科技感风格
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
    <GlowCard glowColor="blue" className="file-card">
      <div className="file-card__content">
        {/* 左侧：文件信息 */}
        <div className="file-card__info">
          {/* 文件图标 */}
          <motion.div
            className="file-card__icon"
            whileHover={{ scale: 1.05 }}
            transition={{ duration: 0.2 }}
          >
            <FileTextOutlined />
          </motion.div>

          {/* 文件详情 */}
          <div className="file-card__details">
            <h3 className="file-card__name">{fileInfo.filename}</h3>
            <div className="file-card__meta">
              <Space size="middle">
                <span className="file-card__meta-item">
                  <FileOutlined className="file-card__meta-icon" />
                  <span>{fileInfo.file_type?.toUpperCase() || '未知'}</span>
                </span>
                {pageCount && (
                  <span className="file-card__meta-item">
                    <span className="file-card__meta-label">页数:</span>
                    <span className="file-card__meta-value">{pageCount}</span>
                  </span>
                )}
                {checkTime && (
                  <span className="file-card__meta-item">
                    <ClockCircleOutlined className="file-card__meta-icon" />
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
              className="file-card__export-btn"
            >
              导出报告
            </Button>
          </Dropdown>
        )}
      </div>

      {/* 装饰性扫描线 */}
      <div className="file-card__scanline" />
    </GlowCard>
  )
}

export default FileCard
