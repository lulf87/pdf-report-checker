/**
 * C08NonEmptyFieldDetail - 非空字段校验详情
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, Tag, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DownOutlined,
  FieldBinaryOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import styles from './C08NonEmptyFieldDetail.module.css'

/**
 * 非空字段校验详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 * @param {Array} props.data.errors - 错误列表
 * @param {Array} props.data.item_checks - 检验项目检查列表
 */
export default function C08NonEmptyFieldDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [], item_checks = [] } = data

  // 只显示非空字段相关的错误
  const emptyFieldErrors = errors.filter((e) =>
    e.details?.error_code?.startsWith('EMPTY_FIELD_')
  )

  const hasErrors = emptyFieldErrors.length > 0

  // 解析错误信息，构建表格数据
  const tableData = emptyFieldErrors.map((error, index) => {
    const details = error.details || {}
    const itemNumber = details.item_number || details.row_index || '-'
    const itemName = details.item_name || '-'

    // 解析错误类型
    let fieldName = '-'
    let fieldValue = '-'
    if (details.error_code === 'EMPTY_FIELD_RESULT') {
      fieldName = '检验结果'
      fieldValue = details.field_value || '/'
    } else if (details.error_code === 'EMPTY_FIELD_CONCLUSION') {
      fieldName = '单项结论'
      fieldValue = details.field_value || '/'
    } else if (details.error_code === 'EMPTY_FIELD_REMARK') {
      fieldName = '备注'
      fieldValue = details.field_value || '/'
    }

    return {
      key: index,
      item_number: itemNumber,
      item_name: itemName,
      field_name: fieldName,
      field_value: fieldValue,
      message: error.message || '字段为空',
    }
  })

  // 表格列定义
  const columns = [
    {
      title: '序号',
      dataIndex: 'item_number',
      key: 'item_number',
      width: 80,
      render: (text) => <span className={styles.numberCell}>{text}</span>,
    },
    {
      title: '检验项目',
      dataIndex: 'item_name',
      key: 'item_name',
      ellipsis: true,
    },
    {
      title: '空字段',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 100,
      render: (text) => (
        <Tag className={`${styles.fieldTag} ${styles.errorTag}`}>{text}</Tag>
      ),
    },
    {
      title: '当前值',
      dataIndex: 'field_value',
      key: 'field_value',
      width: 100,
      render: (text) => (
        <span className={styles.emptyValue}>
          <MinusCircleOutlined /> {text || '(空)'}
        </span>
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

  // 统计空字段类型
  const emptyResultCount = emptyFieldErrors.filter((e) =>
    e.details?.error_code?.includes('RESULT')
  ).length
  const emptyConclusionCount = emptyFieldErrors.filter((e) =>
    e.details?.error_code?.includes('CONCLUSION')
  ).length
  const emptyRemarkCount = emptyFieldErrors.filter((e) =>
    e.details?.error_code?.includes('REMARK')
  ).length

  const stats = [
    { label: '检验结果为空', value: emptyResultCount, status: 'error' },
    { label: '单项结论为空', value: emptyConclusionCount, status: 'warning' },
    { label: '备注为空', value: emptyRemarkCount, status: 'info' },
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
          <FieldBinaryOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>非空字段校验详情</span>
          {hasErrors && (
            <StatusBadge
              status="error"
              text={`${emptyFieldErrors.length} 处空字段`}
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

            {/* 错误提示 */}
            {hasErrors && (
              <div className={styles.errorAlert}>
                <ExclamationCircleOutlined className={styles.errorAlertIcon} />
                <div className={styles.errorAlertContent}>
                  <div className={styles.errorAlertTitle}>非空字段校验失败</div>
                  <div className={styles.errorAlertDesc}>
                    发现 {emptyFieldErrors.length} 处必填字段为空，请补充完整
                  </div>
                </div>
              </div>
            )}

            {/* 详情表格 */}
            {tableData.length > 0 ? (
              <div className={styles.tableWrapper}>
                <Table
                  columns={columns}
                  dataSource={tableData}
                  pagination={{ pageSize: 5, size: 'small' }}
                  size="small"
                  className={styles.dataTable}
                />
              </div>
            ) : (
              <div className={styles.emptyState}>
                <CheckCircleOutlined className={styles.emptyIcon} />
                <p>所有必填字段均已填写</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
