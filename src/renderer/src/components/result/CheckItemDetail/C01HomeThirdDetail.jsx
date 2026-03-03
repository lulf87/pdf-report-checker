/**
 * C01HomeThirdDetail - 首页与第三页一致性比对详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { Table, Tag } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C01: 首页与第三页一致性比对详情组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.errorMessage - 错误信息
 */
function C01HomeThirdDetail({ comparisons = [], passed = true, errorMessage = '' }) {
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
      title: '首页值',
      dataIndex: 'homeValue',
      key: 'homeValue',
      width: '25%',
      render: (text) => <span className={styles.value}>{text || '-'}</span>,
    },
    {
      title: '第三页值',
      dataIndex: 'thirdPageValue',
      key: 'thirdPageValue',
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
          <span className={styles.detailTitle}>字段比对详情</span>
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
        {!passed && errorMessage && (
          <div className={styles.errorMessage}>
            <CloseCircleOutlined className={styles.errorIcon} />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default C01HomeThirdDetail
