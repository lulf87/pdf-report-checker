import React from 'react'
import { Card, Table, Tag, Tooltip, Alert } from 'antd'
import {
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

/**
 * 第三页扩展字段核对 - v2.2 新增功能
 * @param {Object} props
 * @param {Object} props.data - third_page_extended_checks 数据
 */
function ThirdPageExtendedSection({ data }) {
  // 调试日志
  console.log('[ThirdPageExtendedSection] data:', data)

  if (!data) {
    console.log('[ThirdPageExtendedSection] data is null/undefined')
    return null
  }

  // 适配后端返回的数据结构：comparisons 和 errors
  const comparisons = data.comparisons || data.fields_comparison || []
  const errors = data.errors || []

  // 将错误分类为日期格式问题和其他一致性问题
  const date_format_issues = errors.filter(e =>
    e.details?.error_code === 'DATE_FORMAT_ERROR_001' ||
    e.message?.includes('格式不一致')
  )
  const consistency_errors = errors.filter(e =>
    e.details?.error_code !== 'DATE_FORMAT_ERROR_001' &&
    !e.message?.includes('格式不一致')
  )

  // 将 comparisons 映射为前端期望的 fields_comparison 格式
  const fields_comparison = comparisons.map(comp => ({
    field_name: comp.field_name,
    table_value: comp.table_value,
    label_value: comp.ocr_value,
    is_match: comp.is_match,
    format_mismatch: comp.issue_type === 'format_mismatch' ||
                     (comp.issue_type === 'mismatch' && comp.field_name === '生产日期')
  }))

  if (fields_comparison.length === 0) return null

  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
    },
    {
      title: '表格值',
      dataIndex: 'table_value',
      key: 'table_value',
      render: (text) => text || <span className={styles.emptyValue}>/</span>,
    },
    {
      title: '标签值',
      dataIndex: 'label_value',
      key: 'label_value',
      render: (text, record) => {
        const hasIssue = record.format_mismatch || !record.is_match
        return (
          <span className={hasIssue ? styles.formatMismatch : ''}>
            {text || <span className={styles.emptyValue}>/</span>}
            {record.format_mismatch && (
              <Tooltip title="格式不一致">
                <WarningOutlined className={styles.formatWarningIcon} />
              </Tooltip>
            )}
          </span>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'is_match',
      key: 'is_match',
      width: 100,
      render: (isMatch, record) => {
        if (record.format_mismatch) {
          return (
            <Tag color="warning" icon={<WarningOutlined />}>
              格式不一致
            </Tag>
          )
        }
        return isMatch ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>一致</Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>不一致</Tag>
        )
      },
    },
  ]

  const hasIssues = date_format_issues.length > 0 || consistency_errors.length > 0

  return (
    <Card
      title={
        <div className={styles.sectionTitle}>
          <FileTextOutlined />
          <span>第三页扩展字段核对</span>
        </div>
      }
      className={styles.sectionCard}
    >
      {hasIssues && (
        <Alert
          message="发现字段不一致或格式问题"
          description={
            <ul className={styles.issueList}>
              {date_format_issues.map((issue, idx) => (
                <li key={idx}>
                  生产日期格式不一致: {issue.table_format} vs {issue.label_format}
                </li>
              ))}
              {consistency_errors.map((error, idx) => (
                <li key={idx}>{error.message}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          className={styles.sectionAlert}
        />
      )}

      <Table
        columns={columns}
        dataSource={fields_comparison}
        rowKey="field_name"
        pagination={false}
        size="middle"
        rowClassName={(record) =>
          !record.is_match || record.format_mismatch ? styles.rowWarning : ''
        }
      />

      {fields_comparison.length === 0 && (
        <div className={styles.emptyState}>
          <p>未检测到扩展字段数据</p>
        </div>
      )}
    </Card>
  )
}

export default ThirdPageExtendedSection
