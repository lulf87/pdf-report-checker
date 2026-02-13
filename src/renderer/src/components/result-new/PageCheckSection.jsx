/**
 * PageCheckSection - 页码校验区域 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React from 'react'
import { Timeline, Tag } from 'antd'
import {
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import styles from './PageCheckSection.module.css'

/**
 * 页码连续性校验组件
 * @param {Object} props
 * @param {Object} props.data - page_number_check 数据
 */
export default function PageCheckSection({ data }) {
  if (!data || !data.page_numbers) return null

  const { page_numbers = [], continuity_errors = [], total_pages_info } = data

  if (page_numbers.length === 0) return null

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
    <div className={styles.pageCheckWrapper}>
      {/* 头部 */}
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>
          <FileTextOutlined /> 页码连续性校验
        </h3>
        {continuity_errors.length > 0 && (
          <Tag className={`${styles.errorCountTag} ${styles.error}`}>
            {continuity_errors.length} 处错误
          </Tag>
        )}
      </div>

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
  )
}
