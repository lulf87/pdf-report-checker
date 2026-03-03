/**
 * ComparisonTable - 字段比对表格
 * 科技感数据大屏设计系统
 */

import React from 'react'
import { Table, Tag, Typography } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import styles from './ComparisonTable.module.css'

const { Text } = Typography

/**
 * 字段比对表格组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据数组
 * @param {string} props.title - 表格标题
 */
export default function ComparisonTable({ comparisons = [], title = '字段比对' }) {
  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
      render: (text) => (
        <span className={styles.fieldName}>{text}</span>
      ),
    },
    {
      title: '首页值',
      dataIndex: 'first_page_value',
      key: 'first_page_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '第三页值',
      dataIndex: 'third_page_value',
      key: 'third_page_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_match',
      key: 'is_match',
      width: 100,
      render: (isMatch) =>
        isMatch ? (
          <Tag className={`${styles.statusTag} ${styles.success}`}>
            <CheckCircleOutlined /> 一致
          </Tag>
        ) : (
          <Tag className={`${styles.statusTag} ${styles.error}`}>
            <CloseCircleOutlined /> 不一致
          </Tag>
        ),
    },
  ]

  // 计算统计
  const totalFields = comparisons.length
  const matchedFields = comparisons.filter(c => c.is_match).length
  const mismatchedFields = totalFields - matchedFields

  return (
    <div className={styles.comparisonTableWrapper}>
      {/* 头部 */}
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>{title}</h3>
        <div className={styles.summaryBadges}>
          <span className={`${styles.summaryBadge} ${styles.success}`}>
            <CheckCircleOutlined /> {matchedFields} 一致
          </span>
          {mismatchedFields > 0 && (
            <span className={`${styles.summaryBadge} ${styles.error}`}>
              <CloseCircleOutlined /> {mismatchedFields} 不一致
            </span>
          )}
        </div>
      </div>

      {/* 表格 */}
      <Table
        size="small"
        pagination={false}
        dataSource={comparisons}
        rowKey="field_name"
        columns={columns}
        className={styles.dataTable}
        rowClassName={(record) => !record.is_match ? styles.rowMismatch : ''}
      />
    </div>
  )
}

/**
 * 首页与第三页比对专用组件
 */
export function HomeThirdComparison({ data = [] }) {
  return (
    <ComparisonTable
      comparisons={data}
      title="首页与第三页比对"
    />
  )
}

/**
 * 表格值与OCR值比对专用组件
 */
export function TableOcrComparison({ comparisons = [] }) {
  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
      render: (text) => (
        <span className={styles.fieldName}>{text}</span>
      ),
    },
    {
      title: '表格值',
      dataIndex: 'table_value',
      key: 'table_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: 'OCR识别值',
      dataIndex: 'ocr_value',
      key: 'ocr_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_match',
      key: 'is_match',
      width: 100,
      render: (isMatch) =>
        isMatch ? (
          <Tag className={`${styles.statusTag} ${styles.success}`}>
            <CheckCircleOutlined /> 一致
          </Tag>
        ) : (
          <Tag className={`${styles.statusTag} ${styles.error}`}>
            <CloseCircleOutlined /> 不一致
          </Tag>
        ),
    },
  ]

  const totalFields = comparisons.length
  const matchedFields = comparisons.filter(c => c.is_match).length
  const mismatchedFields = totalFields - matchedFields

  return (
    <div className={styles.comparisonTableWrapper}>
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>表格值与OCR值比对</h3>
        <div className={styles.summaryBadges}>
          <span className={`${styles.summaryBadge} ${styles.success}`}>
            <CheckCircleOutlined /> {matchedFields} 一致
          </span>
          {mismatchedFields > 0 && (
            <span className={`${styles.summaryBadge} ${styles.error}`}>
              <CloseCircleOutlined /> {mismatchedFields} 不一致
            </span>
          )}
        </div>
      </div>
      <Table
        size="small"
        pagination={false}
        dataSource={comparisons}
        rowKey="field_name"
        columns={columns}
        className={styles.dataTable}
        rowClassName={(record) => !record.is_match ? styles.rowMismatch : ''}
      />
    </div>
  )
}
