/**
 * C07ConclusionDetail - 检验项目单项结论核对详情
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, Tag, Tooltip } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownOutlined,
  FileSearchOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import styles from './C07ConclusionDetail.module.css'

/**
 * 检验项目单项结论核对详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 * @param {Array} props.data.errors - 错误列表
 * @param {Array} props.data.item_checks - 检验项目检查列表
 * @param {number} props.data.total_items - 检验项目总数
 * @param {number} props.data.correct_conclusions - 正确结论数
 * @param {number} props.data.incorrect_conclusions - 错误结论数
 */
export default function C07ConclusionDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const {
    errors = [],
    item_checks = [],
    total_items = 0,
    correct_conclusions = 0,
    incorrect_conclusions = 0,
  } = data

  // 只显示结论相关的错误
  const conclusionErrors = errors.filter(
    (e) => e.details?.error_type === 'CONCLUSION_MISMATCH'
  )

  const hasErrors = conclusionErrors.length > 0 || incorrect_conclusions > 0

  // 构建表格数据 - 只显示有结论错误的项目
  const tableData = item_checks
    .filter((item) => item.clauses?.some((c) => !c.is_conclusion_correct))
    .flatMap((item) =>
      item.clauses
        .filter((clause) => !clause.is_conclusion_correct)
        .map((clause, idx) => ({
          key: `${item.item_number}-${clause.clause_number}-${idx}`,
          item_number: item.item_number,
          item_name: item.item_name,
          clause_number: clause.clause_number,
          actual_conclusion: clause.conclusion || '/',
          expected_conclusion: clause.expected_conclusion || '合格',
          is_correct: clause.is_conclusion_correct,
        }))
    )

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
      title: '标准条款',
      dataIndex: 'clause_number',
      key: 'clause_number',
      width: 100,
    },
    {
      title: '实际结论',
      dataIndex: 'actual_conclusion',
      key: 'actual_conclusion',
      width: 100,
      render: (text) => (
        <Tag className={`${styles.conclusionTag} ${styles.errorTag}`}>
          {text}
        </Tag>
      ),
    },
    {
      title: '期望结论',
      dataIndex: 'expected_conclusion',
      key: 'expected_conclusion',
      width: 100,
      render: (text) => (
        <Tag className={`${styles.conclusionTag} ${styles.successTag}`}>
          {text}
        </Tag>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: () => (
        <Tooltip title="结论错误">
          <CloseCircleOutlined className={styles.statusIconError} />
        </Tooltip>
      ),
    },
  ]

  // 统计卡片数据
  const stats = [
    { label: '检验项目', value: total_items, status: 'blue' },
    { label: '结论正确', value: correct_conclusions, status: 'success' },
    { label: '结论错误', value: incorrect_conclusions, status: 'error' },
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
          <FileSearchOutlined className={styles.headerIcon} />
          <span className={styles.headerTitle}>单项结论核对详情</span>
          {hasErrors && (
            <StatusBadge
              status="error"
              text={`${incorrect_conclusions} 处错误`}
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
                <InfoCircleOutlined className={styles.errorAlertIcon} />
                <div className={styles.errorAlertContent}>
                  <div className={styles.errorAlertTitle}>结论核对错误</div>
                  <div className={styles.errorAlertDesc}>
                    发现 {incorrect_conclusions} 处单项结论与期望不符，请核对检验结果与结论的逻辑关系
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
                <p>所有单项结论核对正确</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
