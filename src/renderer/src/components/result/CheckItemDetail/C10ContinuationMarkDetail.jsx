/**
 * C10ContinuationMarkDetail - 续表标记检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, WarningOutlined, FileTextOutlined } from '@ant-design/icons'
import { Tag, List } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C10: 续表标记检查详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 */
function C10ContinuationMarkDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [], continuation_marks = [], cross_page_continuations = 0 } = data

  // 只显示续表标记相关的错误
  const continuationErrors = errors.filter(
    (e) =>
      e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_') ||
      e.details?.error_type?.includes('CONTINUATION')
  )

  const hasErrors = continuationErrors.length > 0

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
          <FileTextOutlined className={styles.headerIcon} />
          <span className={styles.detailTitle}>续表标记详情</span>
          {cross_page_continuations > 0 && (
            <Tag className={styles.infoTag}>
              {cross_page_continuations} 处跨页续检
            </Tag>
          )}
          {hasErrors && (
            <Tag className={styles.warningTag}>
              {continuationErrors.length} 处警告
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
            <div className={styles.warningAlert}>
              <WarningOutlined className={styles.warningAlertIcon} />
              <div className={styles.warningAlertContent}>
                <div className={styles.warningAlertTitle}>续表标记警告</div>
                <div className={styles.warningAlertDesc}>
                  发现 {continuationErrors.length} 处续表标记问题
                </div>
              </div>
            </div>
            <List
              className={styles.errorList}
              dataSource={continuationErrors}
              renderItem={(error, index) => (
                <List.Item className={styles.errorListItem}>
                  <div className={styles.errorItem}>
                    <WarningOutlined className={styles.errorItemIcon} />
                    <span className={styles.errorItemText}>{error.message}</span>
                  </div>
                </List.Item>
              )}
            />
          </>
        ) : (
          <div className={styles.emptyState}>
            <CheckCircleOutlined className={styles.emptyIcon} />
            <p>续表标记检查通过</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default C10ContinuationMarkDetail
