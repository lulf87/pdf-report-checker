/**
 * C11PageNumberDetail - 页码连续性校验详情组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useState } from 'react'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, FileTextOutlined } from '@ant-design/icons'
import { Table, Tag, Timeline } from 'antd'
import styles from './CheckItemDetail.module.css'

/**
 * C11: 页码连续性校验详情组件
 * @param {Object} props
 * @param {Object} props.data - 核对结果数据
 */
function C11PageNumberDetail({ data }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!data) return null

  const { page_numbers = [], continuity_errors = [], total_pages_info, passed = true } = data

  const hasErrors = !passed || continuity_errors.length > 0

  // 构建时间线数据
  const timelineItems = page_numbers.map((page, index) => {
    const hasError = page.errors && page.errors.length > 0

    return {
      color: hasError ? 'red' : 'green',
      dot: hasError ? (
        <CloseCircleOutlined className={styles.timelineDotError} />
      ) : (
        <CheckCircleOutlined className={styles.timelineDotSuccess} />
      ),
      children: (
        <div className={styles.pageNumberItem}>
          <div className={styles.pageNumberHeader}>
            <span className={styles.pageLabel}>排版页 {page.page_num}</span>
            <Tag className={styles.pageNumberTag}>
              共{page.total_pages}页 第{page.current_page}页
            </Tag>
          </div>

          {hasError ? (
            <div className={styles.pageErrors}>
              {page.errors.map((error, idx) => (
                <Tag key={idx} className={`${styles.errorTag} ${styles.error}`}>
                  {error.type === 'skip' && '跳号'}
                  {error.type === 'duplicate' && '重复'}
                  {error.type === 'mismatch_total' && '总页数不一致'}
                  {error.type === 'last_page_mismatch' && '末页不匹配'}
                  {!error.type && error.message}
                </Tag>
              ))}
            </div>
          ) : (
            <span className={styles.pageStatusOk}>
              <CheckCircleOutlined /> 页码正确
            </span>
          )}

          {page.is_continuation && (
            <Tag className={`${styles.continuationTag} ${styles.info}`}>续表页</Tag>
          )}
        </div>
      ),
    }
  })

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
          <span className={styles.detailTitle}>页码连续性详情</span>
          {hasErrors && (
            <Tag className={styles.errorTag}>
              {continuity_errors.length} 处错误
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
        {/* 总页数信息 */}
        {total_pages_info && (
          <div className={styles.pageNumberStats}>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>总页数标记:</span>
              <span className={styles.statValue}>{total_pages_info.declared_total || '-'}</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>实际页数:</span>
              <span className={styles.statValue}>{total_pages_info.actual_count || '-'}</span>
            </div>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>状态:</span>
              {total_pages_info.is_match ? (
                <Tag className={`${styles.statusTag} ${styles.success}`}>
                  <CheckCircleOutlined /> 一致
                </Tag>
              ) : (
                <Tag className={`${styles.statusTag} ${styles.error}`}>
                  <CloseCircleOutlined /> 不一致
                </Tag>
              )}
            </div>
          </div>
        )}

        {/* 时间线 */}
        <div className={styles.timelineWrapper}>
          <Timeline items={timelineItems} className={styles.pageNumberTimeline} />
        </div>
      </div>
    </div>
  )
}

export default C11PageNumberDetail
