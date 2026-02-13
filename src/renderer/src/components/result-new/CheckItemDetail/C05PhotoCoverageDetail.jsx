/**
 * C05PhotoCoverageDetail - 照片覆盖性检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, CameraOutlined } from '@ant-design/icons'
import { Tag, List } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C05: 照片覆盖性检查详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件列表
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 总部件数
 * @param {number} props.coveredComponents - 已覆盖部件数
 */
function C05PhotoCoverageDetail({ components = [], passed = true, totalComponents = 0, coveredComponents = 0 }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const uncoveredComponents = components.filter(c => !c.isUnused && c.status !== 'covered')

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
          <span className={styles.detailTitle}>照片覆盖详情</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.summaryText}>{coveredComponents}/{totalComponents} 已覆盖</span>
          <Tag className={passed ? styles.successTag : styles.errorTag}>
            {passed ? '全部覆盖' : '存在未覆盖'}
          </Tag>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        {uncoveredComponents.length > 0 ? (
          <List
            className={styles.coverageList}
            header={<div className={styles.listHeader}>未覆盖部件</div>}
            dataSource={uncoveredComponents}
            renderItem={(item) => (
              <List.Item className={styles.coverageListItem}>
                <div className={styles.coverageItem}>
                  <CameraOutlined className={styles.coverageIcon} />
                  <span className={styles.coverageName}>{item.componentName}</span>
                  <Tag className={styles.errorTag}>未覆盖</Tag>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <div className={styles.emptyState}>
            <CheckCircleOutlined className={styles.emptyIcon} />
            <p>所有部件均已覆盖照片</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default C05PhotoCoverageDetail
