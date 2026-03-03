/**
 * C09SerialNumberDetail - 序号连续性检查详情
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, Tag, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  DownOutlined,
  OrderedListOutlined,
  StepForwardOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import styles from './C09SerialNumberDetail.module.css'

/**
 * 序号连续性检查详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 * @param {Array} props.data.errors - 错误列表
 * @param {Array} props.data.serial_numbers - 序号列表
 */
export default function C09SerialNumberDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [], serial_numbers = [] } = data

  // 只显示序号连续性相关的错误
  const serialNumberErrors = errors.filter(
    (e) =>
      e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
      e.details?.error_type === 'SERIAL_NUMBER_DISCONTINUITY'
  )

  const hasErrors = serialNumberErrors.length > 0

  // 解析序号序列
  const sortedNumbers = [...serial_numbers].sort((a, b) => a - b)

  // 构建序号可视化数据
  const buildSequenceVisualization = () => {
    if (sortedNumbers.length === 0) return []

    const items = []
    let prev = null

    for (let i = 0; i < sortedNumbers.length; i++) {
      const current = sortedNumbers[i]

      // 检查是否有跳号
      if (prev !== null && current > prev + 1) {
        // 添加跳号标记
        items.push({
          type: 'skip',
          from: prev,
          to: current,
          skipped: Array.from({ length: current - prev - 1 }, (_, idx) => prev + idx + 1),
        })
      }

      // 检查是否有重复（简化处理，实际应该根据错误信息判断）
      const isDuplicate = sortedNumbers.indexOf(current) !== sortedNumbers.lastIndexOf(current)

      items.push({
        type: 'number',
        value: current,
        isDuplicate,
      })

      prev = current
    }

    return items
  }

  const sequenceItems = buildSequenceVisualization()

  // 构建错误表格数据
  const errorTableData = serialNumberErrors.map((error, index) => {
    const details = error.details || {}
    const errorType = details.error_type || 'UNKNOWN'

    let errorTypeText = '未知错误'
    let errorTypeStatus = 'error'

    if (errorType === 'SERIAL_NUMBER_SKIP') {
      errorTypeText = '跳号'
      errorTypeStatus = 'warning'
    } else if (errorType === 'SERIAL_NUMBER_DUPLICATE') {
      errorTypeText = '重复'
      errorTypeStatus = 'error'
    } else if (errorType === 'SERIAL_NUMBER_DISCONTINUITY') {
      errorTypeText = '不连续'
      errorTypeStatus = 'warning'
    }

    return {
      key: index,
      position: details.position || details.current_number || '-',
      error_type: errorTypeText,
      error_type_status: errorTypeStatus,
      expected: details.expected || '-',
      actual: details.actual || '-',
      message: error.message || '序号错误',
    }
  })

  // 表格列定义
  const columns = [
    {
      title: '位置',
      dataIndex: 'position',
      key: 'position',
      width: 100,
      render: (text) => <span className={styles.numberCell}>{text}</span>,
    },
    {
      title: '错误类型',
      dataIndex: 'error_type',
      key: 'error_type',
      width: 120,
      render: (text, record) => (
        <Tag
          className={`${styles.errorTypeTag} ${styles[record.error_type_status]}`}
        >
          {text}
        </Tag>
      ),
    },
    {
      title: '期望值',
      dataIndex: 'expected',
      key: 'expected',
      width: 100,
      render: (text) =>
        text !== '-' ? (
          <span className={styles.expectedValue}>{text}</span>
        ) : (
          <span className={styles.dash}>-</span>
        ),
    },
    {
      title: '实际值',
      dataIndex: 'actual',
      key: 'actual',
      width: 100,
      render: (text) =>
        text !== '-' ? (
          <span className={styles.actualValue}>{text}</span>
        ) : (
          <span className={styles.dash}>-</span>
        ),
    },
    {
      title: '说明',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (text) => <span className={styles.messageText}>{text}</span>,
    },
  ]

  // 统计
  const skipCount = serialNumberErrors.filter((e) =>
    e.details?.error_type?.includes('SKIP')
  ).length
  const duplicateCount = serialNumberErrors.filter((e) =>
    e.details?.error_type?.includes('DUPLICATE')
  ).length

  const stats = [
    { label: '总序号数', value: sortedNumbers.length, status: 'blue' },
    { label: '跳号', value: skipCount, status: 'warning' },
    { label: '重复', value: duplicateCount, status: 'error' },
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
          <OrderedListOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>序号连续性检查详情</span>
          {hasErrors && (
            <StatusBadge
              status="warning"
              text={`${serialNumberErrors.length} 处问题`}
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

            {/* 序号序列可视化 */}
            {sortedNumbers.length > 0 && (
              <div className={styles.sequenceSection}>
                <div className={styles.sequenceTitle}>
                  <StepForwardOutlined /> 序号序列
                </div>
                <div className={styles.sequenceVisual}>
                  {sequenceItems.map((item, idx) => {
                    if (item.type === 'skip') {
                      return (
                        <Tooltip
                          key={`skip-${idx}`}
                          title={`跳过: ${item.skipped.join(', ')}`}
                        >
                          <span className={styles.skipIndicator}>
                            <WarningOutlined />
                          </span>
                        </Tooltip>
                      )
                    }
                    return (
                      <span
                        key={`num-${idx}`}
                        className={`${styles.sequenceNumber} ${
                          item.isDuplicate ? styles.duplicate : ''
                        }`}
                      >
                        {item.value}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* 错误表格 */}
            {errorTableData.length > 0 ? (
              <div className={styles.tableWrapper}>
                <div className={styles.tableTitle}>
                  <CloseCircleOutlined /> 错误详情
                </div>
                <Table
                  columns={columns}
                  dataSource={errorTableData}
                  pagination={{ pageSize: 5, size: 'small' }}
                  size="small"
                  className={styles.dataTable}
                />
              </div>
            ) : (
              <div className={styles.emptyState}>
                <CheckCircleOutlined className={styles.emptyIcon} />
                <p>序号连续，无跳号或重复</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
