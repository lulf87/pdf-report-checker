/**
 * C06ChineseLabelDetail - 中文标签覆盖检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, TagOutlined } from '@ant-design/icons'
import { Tag, List } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C06: 中文标签覆盖检查详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件列表
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 总部件数
 * @param {number} props.labeledComponents - 有标签部件数
 */
function C06ChineseLabelDetail({ components = [], passed = true, totalComponents = 0, labeledComponents = 0 }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const unlabeledComponents = components.filter(c => !c.isUnused && c.labelStatus !== 'has_label')

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
          <span className={styles.detailTitle}>中文标签覆盖详情</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.summaryText}>{labeledComponents}/{totalComponents} 有标签</span>
          <Tag className={passed ? styles.successTag : styles.errorTag}>
            {passed ? '全部有标签' : '存在无标签'}
          </Tag>
        </div>
      </div>

      {/* 展开内容 */}
      <div className={`${styles.detailContent} ${isExpanded ? styles.expanded : ''}`}>
        {unlabeledComponents.length > 0 ? (
          <List
            className={styles.coverageList}
            header={<div className={styles.listHeader}>无中文标签部件</div>}
            dataSource={unlabeledComponents}
            renderItem={(item) => (
              <List.Item className={styles.coverageListItem}>
                <div className={styles.coverageItem}>
                  <TagOutlined className={styles.coverageIcon} />
                  <span className={styles.coverageName}>{item.componentName}</span>
                  <Tag className={styles.errorTag}>无标签</Tag>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <div className={styles.emptyState}>
            <CheckCircleOutlined className={styles.emptyIcon} />
            <p>所有部件均包含中文标签</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default C06ChineseLabelDetail
