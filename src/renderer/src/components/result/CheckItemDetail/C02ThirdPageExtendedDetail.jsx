/**
 * C02ThirdPageExtendedDetail - 第三页扩展字段检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { Table, Tag } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C02: 第三页扩展字段检查详情组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.checkType - 检查类型
 */
function C02ThirdPageExtendedDetail({ comparisons = [], passed = true, checkType = 'field_compare' }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const columns = [
    {
      title: '字段名',
      dataIndex: 'fieldName',
      key: 'fieldName',
      width: '25%',
      render: (text) => <span className={styles.fieldName}>{text}</span>,
    },
    {
      title: '表格值',
      dataIndex: 'tableValue',
      key: 'tableValue',
      width: '25%',
      render: (text) => <span className={styles.value}>{text || '-'}</span>,
    },
    {
      title: '标签值',
      dataIndex: 'labelValue',
      key: 'labelValue',
      width: '25%',
      render: (text) => <span className={styles.value}>{text || '-'}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '25%',
      align: 'center',
      render: (status) => (
        <Tag className={status === 'match' ? styles.successTag : styles.errorTag}>
          {status === 'match' ? <><CheckCircleOutlined /> 一致</> : <><CloseCircleOutlined /> 不一致</>}
        </Tag>
      ),
    },
  ]

  const checkTypeLabel = {
    field_compare: '字段比对',
    ocr_compare: 'OCR比对',
    mixed: '混合检查'
  }

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
          <span className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}>
            <DownOutlined />
          </span>
          <span className={styles.detailTitle}>扩展字段比对详情</span>
          <Tag className={styles.infoTag}>{checkTypeLabel[checkType] || checkType}</Tag>
        </div>
        <div className={styles.headerRight}>
          <Tag className={passed ? styles.successTag : styles.errorTag}>
            {passed ? '全部一致' : '存在不一致'}
          </Tag>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        <Table
          columns={columns}
          dataSource={comparisons}
          size="small"
          bordered={false}
          pagination={false}
          rowKey="key"
          className={styles.detailTable}
        />
      </div>
    </div>
  )
}

export default C02ThirdPageExtendedDetail
