/**
 * C10ContinuationMarkDetail - 续表标记检查详情
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, Tag, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  DownOutlined,
  LinkOutlined,
  FileTextOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import styles from './C10ContinuationMarkDetail.module.css'

/**
 * 续表标记检查详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 * @param {Array} props.data.errors - 错误列表
 * @param {Array} props.data.continuation_marks - 续表标记列表
 * @param {number} props.data.cross_page_continuations - 跨页续表数
 */
export default function C10ContinuationMarkDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [], continuation_marks = [], cross_page_continuations = 0 } = data

  // 只显示续表标记相关的错误
  const continuationErrors = errors.filter(
    (e) =>
      e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_') ||
      e.details?.error_type?.includes('CONTINUATION')
  )

  const hasErrors = continuationErrors.length > 0

  // 构建表格数据
  const tableData = continuation_marks.map((mark, index) => {
    const hasError = continuationErrors.some(
      (e) =>
        e.details?.page_num === mark.page_num ||
        e.details?.item_number === mark.item_number
    )

    return {
      key: index,
      page_num: mark.page_num || '-',
      item_number: mark.item_number || '-',
      mark_text: mark.mark_text || '续',
      is_valid: mark.is_valid !== false,
      has_error: hasError,
      error_message: hasError
        ? continuationErrors.find(
            (e) =>
              e.details?.page_num === mark.page_num ||
              e.details?.item_number === mark.item_number
          )?.message || '续表标记错误'
        : null,
    }
  })

  // 表格列定义
  const columns = [
    {
      title: '页码',
      dataIndex: 'page_num',
      key: 'page_num',
      width: 80,
      render: (text) => <span className={styles.numberCell}>{text}</span>,
    },
    {
      title: '序号',
      dataIndex: 'item_number',
      key: 'item_number',
      width: 100,
      render: (text) => (
        <span className={text?.startsWith('续') ? styles.continuationMark : ''}>
          {text}
        </span>
      ),
    },
    {
      title: '续表标记',
      dataIndex: 'mark_text',
      key: 'mark_text',
      width: 100,
      render: (text, record) => (
        <Tag
          className={`${styles.markTag} ${
            record.is_valid ? styles.validMark : styles.invalidMark
          }`}
        >
          {text}
        </Tag>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) =>
        record.has_error ? (
          <Tooltip title={record.error_message}>
            <span className={styles.statusError}>
              <CloseCircleOutlined /> 错误
            </span>
          </Tooltip>
        ) : (
          <span className={styles.statusOk}>
            <CheckCircleOutlined /> 正确
          </span>
        ),
    },
    {
      title: '说明',
      key: 'description',
      ellipsis: true,
      render: (_, record) => (
        <span className={styles.descriptionText}>
          {record.has_error
            ? record.error_message
            : '续表标记格式正确'}
        </span>
      ),
    },
  ]

  // 统计
  const validCount = tableData.filter((m) => m.is_valid && !m.has_error).length
  const invalidCount = tableData.filter((m) => !m.is_valid || m.has_error).length

  const stats = [
    { label: '续表页数', value: cross_page_continuations, status: 'cyan' },
    { label: '标记正确', value: validCount, status: 'success' },
    { label: '标记错误', value: invalidCount, status: 'error' },
  ]

  return (
    <div className={styles.detailWrapper}>
      {/* 折叠头部 */}
      <motion.div
        className={styles.header}
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
      >
        <div className={styles.headerLeft}>
          <LinkOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>续表标记检查详情</span>
          {hasErrors && (
            <StatusBadge
              status="error"
              text={`${invalidCount} 处错误`}
              size="sm"
            />
          )}
          {cross_page_continuations > 0 && !hasErrors && (
            <StatusBadge
              status="cyan"
              text={`续×${cross_page_continuations}`}
              size="sm"
            />
          )}
        </div>
        <div className={styles.headerRight}>
          <motion.span
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <DownOutlined className={styles.expandIcon} />
          </motion.span>
        </div>
      </motion.div>

      {/* 展开内容 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className={styles.content}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            {/* 统计卡片 */}
            <div className={styles.statsGrid}>
              {stats.map((stat, index) => (
                <div
                  key={index}
                  className={`${styles.statCard} ${styles[stat.status]}`}
                >
                  <div className={styles.statValue}>{stat.value}</div>
                  <div className={styles.statLabel}>{stat.label}</div>
                </div>
              ))}
            </div>

            {/* 续表说明 */}
            <div className={styles.infoSection}>
              <div className={styles.infoTitle}>
                <FileTextOutlined />
                续表标记规范
              </div>
              <div className={styles.infoContent}>
                <ul className={styles.infoList}>
                  <li>跨页表格应在续页标注"续"字</li>
                  <li>序号应以"续X"格式标注（如：续1、续2）</li>
                  <li>续表页应保持与首页相同的表头</li>
                </ul>
              </div>
            </div>

            {/* 详情表格 */}
            {tableData.length > 0 ? (
              <div className={styles.tableWrapper}>
                <Table
                  columns={columns}
                  dataSource={tableData}
                  pagination={{ pageSize: 5, size: 'small' }}
                  size="small"
                  className={styles.dataTable}
                  rowClassName={(record) => (record.has_error ? styles.rowError : '')}
                />
              </div>
            ) : (
              <div className={styles.emptyState}>
                <CheckCircleOutlined className={styles.emptyIcon} />
                <p>未发现续表标记或无需续表</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
