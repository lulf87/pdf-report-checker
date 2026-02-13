/**
 * C11PageNumberDetail - 页码连续性校验详情
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, Tag, Timeline, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  DownOutlined,
  FileTextOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  FileDoneOutlined,
} from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import styles from './C11PageNumberDetail.module.css'

/**
 * 页码连续性校验详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 * @param {Array} props.data.page_numbers - 页码列表
 * @param {Array} props.data.continuity_errors - 连续性错误列表
 * @param {Object} props.data.total_pages_info - 总页数信息
 */
export default function C11PageNumberDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const {
    page_numbers = [],
    continuity_errors = [],
    total_pages_info = {},
  } = data

  const hasErrors = continuity_errors.length > 0
  const totalMatch = total_pages_info?.is_match !== false

  // 构建时间线数据
  const timelineItems = page_numbers.map((page, index) => {
    const hasError = page.errors && page.errors.length > 0

    return {
      color: hasError ? 'red' : 'green',
      dot: hasError ? (
        <CloseCircleOutlined className={styles.timelineDotError} />
      ) : (
        <CheckCircleOutlined className={styles.timelineDotSuccess} />
      ),
      children: (
        <div className={styles.pageNumberItem}>
          <div className={styles.pageNumberHeader}>
            <span className={styles.pageLabel}>排版页 {page.page_num}</span>
            <Tag className={styles.pageNumberTag}>
              共{page.total_pages}页 第{page.current_page}页
            </Tag>
          </div>

          {hasError ? (
            <div className={styles.pageErrors}>
              {page.errors.map((error, idx) => (
                <Tag
                  key={idx}
                  className={`${styles.errorTag} ${styles[error.type || 'error']}`}
                >
                  {error.type === 'skip' && '跳号'}
                  {error.type === 'duplicate' && '重复'}
                  {error.type === 'mismatch_total' && '总页数不一致'}
                  {error.type === 'last_page_mismatch' && '末页不匹配'}
                  {!error.type && error.message}
                </Tag>
              ))}
            </div>
          ) : (
            <span className={styles.pageStatusOk}>
              <CheckCircleOutlined /> 页码正确
            </span>
          )}

          {page.is_continuation && (
            <Tag className={`${styles.continuationTag} ${styles.info}`}>
              续表页
            </Tag>
          )}
        </div>
      ),
    }
  })

  // 构建表格数据
  const tableData = page_numbers.map((page, index) => ({
    key: index,
    page_num: page.page_num,
    mark_format: page.mark_format || `共${page.total_pages}页 第${page.current_page}页`,
    continuity: page.errors?.some((e) => e.type === 'skip' || e.type === 'duplicate')
      ? '异常'
      : '连续',
    last_page_check: page.errors?.some((e) => e.type === 'last_page_mismatch')
      ? '不匹配'
      : '匹配',
    has_error: page.errors && page.errors.length > 0,
    errors: page.errors || [],
  }))

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
      title: '标记格式',
      dataIndex: 'mark_format',
      key: 'mark_format',
      render: (text) => <Tag className={styles.formatTag}>{text}</Tag>,
    },
    {
      title: '连续性',
      dataIndex: 'continuity',
      key: 'continuity',
      width: 100,
      render: (text) => (
        <span
          className={
            text === '连续' ? styles.continuityOk : styles.continuityError
          }
        >
          {text === '连续' ? (
            <CheckCircleOutlined />
          ) : (
            <WarningOutlined />
          )}{' '}
          {text}
        </span>
      ),
    },
    {
      title: '末页校验',
      dataIndex: 'last_page_check',
      key: 'last_page_check',
      width: 100,
      render: (text) => (
        <span
          className={
            text === '匹配' ? styles.lastPageOk : styles.lastPageError
          }
        >
          {text === '匹配' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}{' '}
          {text}
        </span>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) =>
        record.has_error ? (
          <Tooltip
            title={record.errors.map((e) => e.message || e.type).join(', ')}
          >
            <StatusBadge status="error" text="错误" size="sm" />
          </Tooltip>
        ) : (
          <StatusBadge status="success" text="正确" size="sm" />
        ),
    },
  ]

  // 统计
  const stats = [
    {
      label: '总页数声明',
      value: total_pages_info?.declared_total || '-',
      status: 'blue',
    },
    {
      label: '实际页数',
      value: total_pages_info?.actual_count || page_numbers.length,
      status: 'cyan',
    },
    {
      label: '页码错误',
      value: continuity_errors.length,
      status: hasErrors ? 'error' : 'success',
    },
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
          <FileTextOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>页码连续性校验详情</span>
          {hasErrors && (
            <StatusBadge
              status="error"
              text={`${continuity_errors.length} 处错误`}
              size="sm"
            />
          )}
          {!totalMatch && (
            <StatusBadge status="warning" text="总页数不一致" size="sm" />
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

            {/* 总页数对比 */}
            {total_pages_info && (
              <div className={styles.totalPagesSection}>
                <div className={styles.totalPagesTitle}>
                  <FileDoneOutlined />
                  总页数校验
                  {!totalMatch && (
                    <StatusBadge
                      status="error"
                      text="不一致"
                      size="sm"
                      className={styles.totalPagesBadge}
                    />
                  )}
                  {totalMatch && (
                    <StatusBadge
                      status="success"
                      text="一致"
                      size="sm"
                      className={styles.totalPagesBadge}
                    />
                  )}
                </div>
                <div className={styles.totalPagesContent}>
                  <div className={styles.totalPagesItem}>
                    <span className={styles.totalPagesLabel}>声明总页数:</span>
                    <span className={styles.totalPagesValue}>
                      {total_pages_info.declared_total || '-'}
                    </span>
                  </div>
                  <div className={styles.totalPagesItem}>
                    <span className={styles.totalPagesLabel}>实际页数:</span>
                    <span className={styles.totalPagesValue}>
                      {total_pages_info.actual_count || page_numbers.length}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 页码时间线 */}
            <div className={styles.timelineSection}>
              <div className={styles.timelineTitle}>
                <FileTextOutlined />
                页码序列
              </div>
              <div className={styles.timelineWrapper}>
                <Timeline
                  items={timelineItems}
                  className={styles.pageNumberTimeline}
                />
              </div>
            </div>

            {/* 详情表格 */}
            {tableData.length > 0 && (
              <div className={styles.tableWrapper}>
                <div className={styles.tableTitle}>详细校验结果</div>
                <Table
                  columns={columns}
                  dataSource={tableData}
                  pagination={{ pageSize: 5, size: 'small' }}
                  size="small"
                  className={styles.dataTable}
                  rowClassName={(record) =>
                    record.has_error ? styles.rowError : ''
                  }
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
