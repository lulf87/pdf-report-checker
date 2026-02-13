/**
 * InspectionTable - 检验项目表格
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { Table, Tag, Input, Select, Tooltip, Badge, Alert, List } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileSearchOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import styles from './InspectionTable.module.css'

const { Option } = Select
const { Search } = Input

/**
 * 检验项目表格组件
 * @param {Object} props
 * @param {Object} props.data - inspection_item_check 数据
 */
export default function InspectionTable({ data }) {
  const [filter, setFilter] = useState('all')
  const [searchText, setSearchText] = useState('')

  // 检查数据是否存在
  if (!data) return null

  const hasTable = data.has_table === true || data.has_table === 'true'
  if (!hasTable) {
    return (
      <div className={styles.inspectionTableWrapper}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>
            <FileSearchOutlined /> 检验项目核对
          </h3>
        </div>
        <div className={styles.emptyState}>
          <InfoCircleOutlined className={styles.emptyIcon} />
          <p>未检测到检验项目表格</p>
        </div>
      </div>
    )
  }

  const errors = data.errors || []
  const emptyFieldErrors = errors.filter(e =>
    e.details?.error_code?.startsWith('EMPTY_FIELD_')
  )
  const serialNumberErrors = errors.filter(e =>
    e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
    e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_')
  )

  // 统计数据
  const stats = [
    { label: '检验项目', value: data.total_items || 0, color: 'blue' },
    { label: '结论正确', value: data.correct_conclusions || 0, color: 'green' },
    { label: '结论错误', value: data.incorrect_conclusions || 0, color: 'red' },
  ]

  // 过滤数据
  const filteredItems = (data.item_checks || []).filter(item => {
    const matchesSearch = item.item_name?.toLowerCase().includes(searchText.toLowerCase()) ||
                         item.item_number?.includes(searchText)
    const matchesFilter = filter === 'all' ? true :
                         filter === 'correct' ? item.status === 'pass' :
                         item.status !== 'pass'
    return matchesSearch && matchesFilter
  })

  // 表格列定义
  const columns = [
    {
      title: '序号',
      dataIndex: 'item_number',
      key: 'item_number',
      width: 80,
      render: (text) => {
        const isContinuation = text?.startsWith('续')
        return (
          <span className={isContinuation ? styles.continuationMark : ''}>
            {text}
          </span>
        )
      },
    },
    {
      title: '检验项目',
      dataIndex: 'item_name',
      key: 'item_name',
      ellipsis: true,
    },
    {
      title: '标准条款',
      key: 'clause_count',
      width: 100,
      render: (_, record) => (record.clauses || []).length,
    },
    {
      title: '单项结论核对',
      key: 'conclusion_summary',
      width: 150,
      render: (_, record) => {
        const clauses = record.clauses || []
        const correctCount = clauses.filter(c => c.is_conclusion_correct).length
        const totalCount = clauses.length
        const allCorrect = correctCount === totalCount

        return (
          <Tag className={`${styles.statusTag} ${allCorrect ? styles.success : styles.error}`}>
            {allCorrect ? (
              <><CheckCircleOutlined /> {correctCount}/{totalCount}</>
            ) : (
              <><CloseCircleOutlined /> {correctCount}/{totalCount}</>
            )}
          </Tag>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag className={`${styles.statusTag} ${status === 'pass' ? styles.success : status === 'fail' ? styles.error : styles.warning}`}>
          {status === 'pass' ? '通过' : status === 'fail' ? '失败' : '警告'}
        </Tag>
      ),
    },
  ]

  // 展开行内容
  const expandedRowRender = (record) => {
    const clauses = record.clauses || []
    return (
      <div className={styles.expandedContent}>
        <Table
          columns={[
            {
              title: '标准条款',
              dataIndex: 'clause_number',
              key: 'clause_number',
              width: 120,
            },
            {
              title: '标准要求',
              key: 'requirements',
              render: (_, clause) => (
                <div className={styles.requirementsList}>
                  {(clause.requirements || []).map((req, idx) => (
                    <div key={idx} className={styles.requirementItem}>
                      <div className={styles.requirementText}>{req.requirement_text}</div>
                      <div className={styles.requirementMeta}>
                        <span>结果: {req.inspection_result || '-'}</span>
                        {req.remark && <span>备注: {req.remark}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ),
            },
            {
              title: '单项结论',
              key: 'conclusion',
              width: 200,
              render: (_, clause) => (
                <div className={styles.conclusionCell}>
                  <div className={styles.conclusionRow}>
                    <span className={styles.conclusionLabel}>实际:</span>
                    <Tag className={clause.is_conclusion_correct ? styles.success : styles.error}>
                      {clause.conclusion || '/'}
                    </Tag>
                  </div>
                  {!clause.is_conclusion_correct && clause.expected_conclusion && (
                    <div className={styles.conclusionRow}>
                      <span className={styles.conclusionLabel}>期望:</span>
                      <Tag className={styles.info}>{clause.expected_conclusion}</Tag>
                    </div>
                  )}
                </div>
              ),
            },
            {
              title: '状态',
              key: 'status',
              width: 80,
              render: (_, clause) => (
                clause.is_conclusion_correct ? (
                  <CheckCircleOutlined className={styles.statusIconCorrect} />
                ) : (
                  <Tooltip title="结论错误">
                    <CloseCircleOutlined className={styles.statusIconError} />
                  </Tooltip>
                )
              ),
            },
          ]}
          dataSource={clauses}
          rowKey="clause_number"
          pagination={false}
          size="small"
          rowClassName={(clause) => !clause.is_conclusion_correct ? styles.rowError : ''}
        />
      </div>
    )
  }

  const totalErrors = (data.incorrect_conclusions || 0) + emptyFieldErrors.length + serialNumberErrors.length

  return (
    <div className={styles.inspectionTableWrapper}>
      {/* 头部 */}
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>
          <FileSearchOutlined /> 检验项目核对
          {data.cross_page_continuations > 0 && (
            <Badge count={`续×${data.cross_page_continuations}`} className={styles.continuationBadge} />
          )}
        </h3>
        <Tag className={`${styles.statusTag} ${totalErrors === 0 ? styles.success : styles.error}`}>
          {totalErrors === 0 ? '全部正确' : `${totalErrors} 处错误`}
        </Tag>
      </div>

      {/* 统计卡片 */}
      <div className={styles.statsGrid}>
        {stats.map((stat, index) => (
          <div key={index} className={`${styles.statCard} ${styles[stat.color]}`}>
            <div className={styles.statValue}>{stat.value}</div>
            <div className={styles.statLabel}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* 错误提示 */}
      {emptyFieldErrors.length > 0 && (
        <Alert
          message="非空字段校验错误"
          description={
            <List
              size="small"
              dataSource={emptyFieldErrors}
              renderItem={(error) => (
                <List.Item style={{ color: 'var(--color-error-light, #f87171)' }}>
                  {error.message}
                </List.Item>
              )}
            />
          }
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          className={styles.errorAlert}
        />
      )}

      {/* 筛选栏 */}
      <div className={styles.filterBar}>
        <Select value={filter} onChange={setFilter} className={styles.filterSelect}>
          <Option value="all">全部显示</Option>
          <Option value="correct">仅正确</Option>
          <Option value="incorrect">仅错误</Option>
        </Select>

        <Search
          placeholder="搜索检验项目或序号"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className={styles.searchInput}
          allowClear
        />

        <button className={styles.exportButton}>
          <DownloadOutlined /> 导出明细
        </button>
      </div>

      {/* 表格 */}
      <Table
        columns={columns}
        dataSource={filteredItems}
        rowKey={(record) => `${record.item_number}-${record.item_name}`}
        expandable={{
          expandedRowRender,
          expandRowByClick: true,
        }}
        pagination={{ pageSize: 10 }}
        size="middle"
        className={styles.dataTable}
        rowClassName={(record) => record.status !== 'pass' ? styles.rowError : ''}
      />
    </div>
  )
}
