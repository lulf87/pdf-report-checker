/**
 * C03DateFormatDetail - 生产日期格式检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { Tag } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C03: 生产日期格式检查详情组件
 * @param {Object} props
 * @param {string} props.tableFormat - 表格日期格式
 * @param {string} props.labelFormat - 标签日期格式
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.tableDate - 表格日期值
 * @param {string} props.labelDate - 标签日期值
 */
function C03DateFormatDetail({
  tableFormat = '',
  labelFormat = '',
  passed = true,
  tableDate = '',
  labelDate = ''
}) {
  const [isExpanded, setIsExpanded] = useState(false)

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
          <span className={styles.detailTitle}>日期格式比对详情</span>
        </div>
        <div className={styles.headerRight}>
          <Tag className={passed ? styles.successTag : styles.errorTag}>
            {passed ? '格式一致' : '格式不一致'}
          </Tag>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        <div className={styles.comparisonGrid}>
          <div className={styles.comparisonItem}>
            <div className={styles.comparisonLabel}>表格日期</div>
            <div className={styles.comparisonValue}>{tableDate || '-'}</div>
            <div className={styles.comparisonFormat}>格式: {tableFormat || '-'}</div>
          </div>
          <div className={styles.comparisonDivider}>
            {passed ? (
              <CheckCircleOutlined className={styles.matchIcon} />
            ) : (
              <CloseCircleOutlined className={styles.mismatchIcon} />
            )}
          </div>
          <div className={styles.comparisonItem}>
            <div className={styles.comparisonLabel}>标签日期</div>
            <div className={styles.comparisonValue}>{labelDate || '-'}</div>
            <div className={styles.comparisonFormat}>格式: {labelFormat || '-'}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default C03DateFormatDetail
