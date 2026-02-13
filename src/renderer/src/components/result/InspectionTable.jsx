/**
 * InspectionTable - 检验项目表格 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState, useMemo, useCallback, memo } from 'react'
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
 * 统计卡片组件
 */
const StatCard = memo(function StatCard({ label, value, color }) {
  return (
    <div className={`${styles.statCard} ${styles[color]}`}>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  )
})

/**
 * 错误提示组件
 */
const ErrorAlert = memo(function ErrorAlert({ errors }) {
  if (errors.length === 0) return null

  return (
    <Alert
      message="非空字段校验错误"
      description={
        <List
          size="small"
          dataSource={errors}
          renderItem={(error) => (
            <List.Item className={styles.errorListItem}>
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
  )
})

/**
 * 展开行内容组件
 */
const ExpandedRowContent = memo(function ExpandedRowContent({ record }) {
  const clauses = record.clauses || []

  const columns = useMemo(() => [
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
            <Tag className={clause.is_conclusion_correct ? styles.successTag : styles.errorTag}>
              {clause.conclusion || '/'}
            </Tag>
          </div>
          {!clause.is_conclusion_correct && clause.expected_conclusion && (
            <div className={styles.conclusionRow}>
              <span className={styles.conclusionLabel}>期望:</span>
              <Tag className={styles.infoTag}>{clause.expected_conclusion}</Tag>
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
  ], [])

  return (
    <div className={styles.expandedContent}>
      <Table
        columns={columns}
        dataSource={clauses}
        rowKey="clause_number"
        pagination={false}
        size="small"
        rowClassName={(clause) => !clause.is_conclusion_correct ? styles.rowError : ''}
        className={styles.nestedTable}
      />
    </div>
  )
})

/**
 * 检验项目表格组件
 * @param {Object} props
 * @param {Object} props.data - inspection_item_check 数据
 */
function InspectionTable({ data }) {
  const [filter, setFilter] = useState('all')
  const [searchText, setSearchText] = useState('')
  const [expandedRowKeys, setExpandedRowKeys] = useState([])

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

  // 使用useMemo缓存错误分类结果
  const { emptyFieldErrors, serialNumberErrors, totalErrors } = useMemo(() => {
    const errors = data.errors || []
    const emptyFieldErrors = errors.filter(e =>
      e.details?.error_code?.startsWith('EMPTY_FIELD_')
    )
    const serialNumberErrors = errors.filter(e =>
      e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
      e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_')
    )
    const totalErrors = (data.incorrect_conclusions || 0) + emptyFieldErrors.length + serialNumberErrors.length

    return { emptyFieldErrors, serialNumberErrors, totalErrors }
  }, [data.errors, data.incorrect_conclusions])

  // 统计数据 - useMemo缓存
  const stats = useMemo(() => [
    { label: '检验项目', value: data.total_items || 0, color: 'blue' },
    { label: '结论正确', value: data.correct_conclusions || 0, color: 'green' },
    { label: '结论错误', value: data.incorrect_conclusions || 0, color: 'red' },
  ], [data.total_items, data.correct_conclusions, data.incorrect_conclusions])

  // 过滤数据 - useMemo缓存
  const filteredItems = useMemo(() => {
    return (data.item_checks || []).filter(item => {
      const matchesSearch = item.item_name?.toLowerCase().includes(searchText.toLowerCase()) ||
                           item.item_number?.includes(searchText)
      const matchesFilter = filter === 'all' ? true :
                           filter === 'correct' ? item.status === 'pass' :
                           item.status !== 'pass'
      return matchesSearch && matchesFilter
    })
  }, [data.item_checks, searchText, filter])

  // 表格列定义 - useMemo缓存
  const columns = useMemo(() => [
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
          <Tag className={`${styles.statusTag} ${allCorrect ? styles.successTag : styles.errorTag}`}>
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
        <Tag className={`${styles.statusTag} ${status === 'pass' ? styles.successTag : status === 'fail' ? styles.errorTag : styles.warningTag}`}>
          {status === 'pass' ? '通过' : status === 'fail' ? '失败' : '警告'}
        </Tag>
      ),
    },
  ], [])

  // 展开行渲染 - useCallback缓存
  const expandedRowRender = useCallback((record) => {
    return <ExpandedRowContent record={record} />
  }, [])

  // 处理展开行变化
  const handleExpandChange = useCallback((expandedKeys) => {
    setExpandedRowKeys(expandedKeys)
  }, [])

  // 处理搜索变化 - useCallback缓存
  const handleSearchChange = useCallback((e) => {
    setSearchText(e.target.value)
  }, [])

  // 处理筛选变化 - useCallback缓存
  const handleFilterChange = useCallback((value) => {
    setFilter(value)
  }, [])

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
        <Tag className={`${styles.statusTag} ${totalErrors === 0 ? styles.successTag : styles.errorTag}`}>
          {totalErrors === 0 ? '全部正确' : `${totalErrors} 处错误`}
        </Tag>
      </div>

      {/* 统计卡片 */}
      <div className={styles.statsGrid}>
        {stats.map((stat, index) => (
          <StatCard key={index} {...stat} />
        ))}
      </div>

      {/* 错误提示 */}
      <ErrorAlert errors={emptyFieldErrors} />

      {/* 筛选栏 */}
      <div className={styles.filterBar}>
        <Select value={filter} onChange={handleFilterChange} className={styles.filterSelect}>
          <Option value="all">全部显示</Option>
          <Option value="correct">仅正确</Option>
          <Option value="incorrect">仅错误</Option>
        </Select>

        <Search
          placeholder="搜索检验项目或序号"
          value={searchText}
          onChange={handleSearchChange}
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
          expandedRowKeys,
          onExpandedRowsChange: handleExpandChange,
          expandRowByClick: true,
        }}
        pagination={{
          pageSize: 10,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 项`,
        }}
        size="middle"
        className={styles.dataTable}
        rowClassName={(record) => record.status !== 'pass' ? styles.rowError : ''}
        scroll={{ y: 400 }}
      />
    </div>
  )
}

// 使用memo包装，避免不必要的重渲染
export default memo(InspectionTable)
