import React, { useState } from 'react'
import { Card, Table, Tag, Button, Input, Select, Tooltip, Badge, Collapse, Alert, List } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileSearchOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  SwapOutlined,
  ExclamationCircleOutlined,
  FieldNumberOutlined,
  FormOutlined,
} from '@ant-design/icons'
import StatCard from './StatCard'
import styles from './styles.module.css'

const { Option } = Select
const { Panel } = Collapse

/**
 * 检验项目核对区域 - v2.1 新增功能
 * @param {Object} props
 * @param {Object} props.data - inspection_item_check 数据
 */
function InspectionItemSection({ data }) {
  const [filter, setFilter] = useState('all') // all | correct | incorrect
  const [searchText, setSearchText] = useState('')

  // 调试日志
  console.log('[InspectionItemSection] data:', data)

  // 检查数据是否存在
  if (!data) {
    console.log('[InspectionItemSection] data is null/undefined')
    return null
  }

  // 检查 has_table 字段（支持布尔值和字符串）
  const hasTable = data.has_table === true || data.has_table === 'true'
  if (!hasTable) {
    return (
      <Card
        title="检验项目核对"
        className={styles.sectionCard}
      >
        <div className={styles.emptyState}>
          <InfoCircleOutlined className={styles.emptyIcon} />
          <p>未检测到检验项目表格</p>
        </div>
      </Card>
    )
  }

  // 从 errors 中分类统计错误
  const errors = data.errors || []
  const emptyFieldErrors = errors.filter(e =>
    e.details?.error_code?.startsWith('EMPTY_FIELD_')
  )
  const serialNumberErrors = errors.filter(e =>
    e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
    e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_')
  )
  const conclusionErrors = errors.filter(e =>
    e.details?.error_code?.startsWith('CONCLUSION_MISMATCH_')
  )

  // 统计卡片数据
  const stats = [
    {
      title: '检验项目',
      value: data.total_items,
      subtitle: `${data.total_clauses} 条款`,
      icon: <FileSearchOutlined />,
      color: 'medical',
    },
    {
      title: '结论正确',
      value: data.correct_conclusions,
      subtitle: '条正确',
      icon: <CheckCircleOutlined />,
      color: 'pass',
    },
    {
      title: '结论错误',
      value: data.incorrect_conclusions,
      subtitle: '条错误',
      icon: <CloseCircleOutlined />,
      color: data.incorrect_conclusions > 0 ? 'fail' : 'pass',
    },
  ]

  // V2.2 新增：非空字段错误统计
  if (emptyFieldErrors.length > 0) {
    stats.push({
      title: '非空校验',
      value: emptyFieldErrors.length,
      subtitle: '处空值',
      icon: <FormOutlined />,
      color: 'fail',
    })
  }

  // V2.2 新增：序号连续性错误统计
  if (serialNumberErrors.length > 0) {
    stats.push({
      title: '序号校验',
      value: serialNumberErrors.length,
      subtitle: '处错误',
      icon: <FieldNumberOutlined />,
      color: 'fail',
    })
  }

  if (data.cross_page_continuations > 0) {
    stats.push({
      title: '跨页续表',
      value: data.cross_page_continuations,
      subtitle: '处续表',
      icon: <SwapOutlined />,
      color: 'warning',
    })
  }

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
          <Tag
            color={allCorrect ? 'success' : 'error'}
            className={styles.conclusionTag}
          >
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
        <Tag color={status === 'pass' ? 'success' : status === 'fail' ? 'error' : 'warning'}>
          {status === 'pass' ? '通过' : status === 'fail' ? '失败' : '警告'}
        </Tag>
      ),
    },
  ]

  // V2.2 新增：渲染非空字段错误列表
  const renderEmptyFieldErrors = () => {
    if (emptyFieldErrors.length === 0) return null

    return (
      <Alert
        message="非空字段校验错误"
        description={
          <List
            size="small"
            dataSource={emptyFieldErrors}
            renderItem={(error) => (
              <List.Item>
                <span style={{ color: '#ef4444' }}>{error.message}</span>
              </List.Item>
            )}
          />
        }
        type="error"
        showIcon
        icon={<ExclamationCircleOutlined />}
        style={{ marginBottom: 16 }}
      />
    )
  }

  // V2.2 新增：渲染序号连续性错误列表
  const renderSerialNumberErrors = () => {
    if (serialNumberErrors.length === 0) return null

    return (
      <Alert
        message="序号连续性校验错误"
        description={
          <List
            size="small"
            dataSource={serialNumberErrors}
            renderItem={(error) => (
              <List.Item>
                <span style={{ color: '#ef4444' }}>{error.message}</span>
              </List.Item>
            )}
          />
        }
        type="error"
        showIcon
        icon={<ExclamationCircleOutlined />}
        style={{ marginBottom: 16 }}
      />
    )
  }

  // 展开行内容 - 标准条款详情
  const expandedRowRender = (record) => {
    const clauses = record.clauses || []
    return (
      <div className={styles.clauseDetailPanel}>
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
                    <Tag color={clause.is_conclusion_correct ? 'success' : 'error'}>
                      {clause.conclusion || '/'}
                    </Tag>
                  </div>
                  {!clause.is_conclusion_correct && (
                    <div className={styles.conclusionRow}>
                      <span className={styles.conclusionLabel}>期望:</span>
                      <Tag color="processing">{clause.expected_conclusion}</Tag>
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

  return (
    <Card
      title={
        <div className={styles.sectionTitle}>
          <FileSearchOutlined />
          <span>检验项目核对</span>
          {data.cross_page_continuations > 0 && (
            <Badge
              count={`续×${data.cross_page_continuations}`}
              className={styles.continuationBadge}
            />
          )}
        </div>
      }
      className={styles.sectionCard}
      extra={
        (() => {
          const totalErrors = data.incorrect_conclusions + emptyFieldErrors.length + serialNumberErrors.length
          return (
            <Tag color={totalErrors === 0 ? 'success' : 'error'}>
              {totalErrors === 0
                ? '全部正确'
                : `${totalErrors} 处错误`}
            </Tag>
          )
        })()
      }
    >
      {/* 统计卡片 */}
      <div className={styles.statsGrid}>
        {stats.map((stat, index) => (
          <StatCard key={index} {...stat} />
        ))}
      </div>

      {/* V2.2 新增：非空字段错误展示 */}
      {renderEmptyFieldErrors()}

      {/* V2.2 新增：序号连续性错误展示 */}
      {renderSerialNumberErrors()}

      {/* 筛选栏 */}
      <div className={styles.filterBar}>
        <Select
          value={filter}
          onChange={setFilter}
          className={styles.filterSelect}
        >
          <Option value="all">全部显示</Option>
          <Option value="correct">仅正确</Option>
          <Option value="incorrect">仅错误</Option>
        </Select>

        <Input.Search
          placeholder="搜索检验项目或序号"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className={styles.searchInput}
        />

        <Button
          icon={<DownloadOutlined />}
          className={styles.exportButton}
        >
          导出明细
        </Button>
      </div>

      {/* 详细表格 */}
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
        rowClassName={(record) => record.status !== 'pass' ? styles.rowError : ''}
      />
    </Card>
  )
}

export default InspectionItemSection
