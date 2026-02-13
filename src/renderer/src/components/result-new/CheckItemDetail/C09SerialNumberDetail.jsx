/**
 * C09SerialNumberDetail - 序号连续性检查详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, WarningOutlined, NumberOutlined } from '@ant-design/icons'
import { Tag, List } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C09: 序号连续性检查详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 */
function C09SerialNumberDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { errors = [], serial_numbers = [] } = data

  // 只显示序号连续性相关的错误
  const serialNumberErrors = errors.filter(
    (e) =>
      e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
      e.details?.error_type === 'SERIAL_NUMBER_DISCONTINUITY'
  )

  const hasErrors = serialNumberErrors.length > 0

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
          <NumberOutlined className={styles.headerIcon} />
          <span className={styles.detailTitle}>序号连续性详情</span>
          {hasErrors && (
            <Tag className={styles.warningTag}>
              {serialNumberErrors.length} 处警告
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
                <div className={styles.warningAlertTitle}>序号连续性警告</div>
                <div className={styles.warningAlertDesc}>
                  发现 {serialNumberErrors.length} 处序号不连续或与产品编号/批号不一致
                </div>
              </div>
            </div>
            <List
              className={styles.errorList}
              dataSource={serialNumberErrors}
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
            <p>序号连续性检查通过</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default C09SerialNumberDetail
