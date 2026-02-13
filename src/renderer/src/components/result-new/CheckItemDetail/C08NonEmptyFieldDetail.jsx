/**
 * C08NonEmptyFieldDetail - 非空字段校验详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { Table, Tag, List } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C08: 非空字段校验详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 */
function C08NonEmptyFieldDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [] } = data

  // 只显示非空字段相关的错误
  const emptyFieldErrors = errors.filter(
    (e) => e.details?.error_code?.startsWith('EMPTY_FIELD_')
  )

  const hasErrors = emptyFieldErrors.length > 0

  // 构建表格数据
  const tableData = emptyFieldErrors.map((error, index) => ({
    key: index,
    item_number: error.details?.item_number || '-',
    item_name: error.details?.item_name || '-',
    field_name: error.details?.field_name || '-',
    message: error.message,
  }))

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
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
      render: (text) => <Tag className={styles.fieldTag}>{text}</Tag>,
    },
    {
      title: '错误信息',
      dataIndex: 'message',
      key: 'message',
      render: (text) => <span className={styles.errorText}>{text}</span>,
    },
  ]

  return (
    <div className={styles.checkDetail}>
      {/* 折叠头部 */}
      <div
        className={styles.detailHeader}
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setIsExpanded(!isExpanded)}
      >
        <div className={styles.headerLeft}>
          <ExclamationCircleOutlined className={styles.headerIcon} />
          <span className={styles.detailTitle}>非空字段校验详情</span>
          {hasErrors && (
            <Tag className={styles.errorTag}>
              {emptyFieldErrors.length} 处错误
            </Tag>
          )}
        </div>
        <div className={styles.headerRight}>
          <span className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}>
            <DownOutlined />
          </span>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        {hasErrors ? (
          <>
            <div className={styles.errorAlert}>
              <ExclamationCircleOutlined className={styles.errorAlertIcon} />
              <div className={styles.errorAlertContent}>
                <div className={styles.errorAlertTitle}>非空字段校验错误</div>
                <div className={styles.errorAlertDesc}>
                  发现 {emptyFieldErrors.length} 处非空字段为空，请补充完整
                </div>
              </div>
            </div>
            <div className={styles.tableWrapper}>
              <Table
                columns={columns}
                dataSource={tableData}
                pagination={{ pageSize: 5, size: 'small' }}
                size="small"
                className={styles.detailTable}
              />
            </div>
          </>
        ) : (
          <div className={styles.emptyState}>
            <CheckCircleOutlined className={styles.emptyIcon} />
            <p>所有非空字段校验通过</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default C08NonEmptyFieldDetail
