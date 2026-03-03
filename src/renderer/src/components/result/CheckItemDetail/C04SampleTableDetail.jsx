/**
 * C04SampleTableDetail - 样品描述表格检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { Table, Tag, Collapse } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C04: 样品描述表格检查详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件列表
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 总部件数
 * @param {number} props.passedComponents - 通过部件数
 */
function C04SampleTableDetail({ components = [], passed = true, totalComponents = 0, passedComponents = 0 }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const columns = [
    {
      title: '字段名',
      dataIndex: 'fieldName',
      key: 'fieldName',
      render: (text) => <span className={styles.fieldName}>{text}</span>,
    },
    {
      title: '表格值',
      dataIndex: 'tableValue',
      key: 'tableValue',
      render: (text) => <span className={styles.value}>{text || '-'}</span>,
    },
    {
      title: '标签值',
      dataIndex: 'labelValue',
      key: 'labelValue',
      render: (text) => <span className={styles.value}>{text || '-'}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      align: 'center',
      render: (status) => (
        <Tag className={status === 'match' ? styles.successTag : styles.errorTag}>
          {status === 'match' ? <><CheckCircleOutlined /> 一致</> : <><CloseCircleOutlined /> 不一致</>}
        </Tag>
      ),
    },
  ]

  const collapseItems = components.map((component, index) => ({
    key: component.componentName || index,
    label: (
      <div className={styles.componentHeader}>
        <span className={styles.componentName}>{component.componentName || `部件 ${index + 1}`}</span>
        <Tag className={component.passed ? styles.successTag : styles.errorTag}>
          {component.passed ? '通过' : '失败'}
        </Tag>
      </div>
    ),
    children: (
      <Table
        columns={columns}
        dataSource={component.fields || []}
        size="small"
        bordered={false}
        pagination={false}
        rowKey="fieldName"
        className={styles.detailTable}
      />
    ),
  }))

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
          <span className={styles.detailTitle}>样品描述表格详情</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.summaryText}>{passedComponents}/{totalComponents} 通过</span>
          <Tag className={passed ? styles.successTag : styles.errorTag}>
            {passed ? '全部通过' : '存在错误'}
          </Tag>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        <Collapse
          items={collapseItems}
          className={styles.componentCollapse}
          defaultActiveKey={components.filter(c => !c.passed).map(c => c.componentName)}
        />
      </div>
    </div>
  )
}

export default C04SampleTableDetail
