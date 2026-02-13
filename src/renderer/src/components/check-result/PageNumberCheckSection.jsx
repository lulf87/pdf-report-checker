import React from 'react'
import { Card, Timeline, Tag, Tooltip } from 'antd'
import {
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

/**
 * 页码连续性校验 - v2.2 新增功能
 * @param {Object} props
 * @param {Object} props.data - page_number_check 数据
 */
function PageNumberCheckSection({ data }) {
  // 调试日志
  console.log('[PageNumberCheckSection] data:', data)

  if (!data || !data.page_numbers) {
    console.log('[PageNumberCheckSection] missing data or page_numbers')
    return null
  }

  const { page_numbers = [], continuity_errors = [], total_pages_info } = data

  if (page_numbers.length === 0) return null

  // 构建时间线数据
  const timelineItems = page_numbers.map((page, index) => {
    const hasError = page.errors && page.errors.length > 0

    return {
      color: hasError ? 'red' : 'green',
      dot: hasError ? <CloseCircleOutlined /> : <CheckCircleOutlined />,
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
                <Tag key={idx} color="error" className={styles.errorTag}>
                  {error.type === 'skip' && '跳号'}
                  {error.type === 'duplicate' && '重复'}
                  {error.type === 'mismatch_total' && '总页数不一致'}
                  {error.type === 'last_page_mismatch' && '末页不匹配'}
                </Tag>
              ))}
            </div>
          ) : (
            <span className={styles.pageStatusOk}>页码正确</span>
          )}

          {page.is_continuation && (
            <Tag color="blue" className={styles.continuationTag}>续表页</Tag>
          )}
        </div>
      ),
    }
  })

  return (
    <Card
      title={
        <div className={styles.sectionTitle}>
          <FileTextOutlined />
          <span>页码连续性校验</span>
          {continuity_errors.length > 0 && (
            <Tag color="error" className={styles.errorCountTag}>
              {continuity_errors.length} 处错误
            </Tag>
          )}
        </div>
      }
      className={styles.sectionCard}
    >
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
              <Tag color="success" icon={<CheckCircleOutlined />}>一致</Tag>
            ) : (
              <Tag color="error" icon={<CloseCircleOutlined />}>不一致</Tag>
            )}
          </div>
        </div>
      )}

      <Timeline items={timelineItems} className={styles.pageNumberTimeline} />
    </Card>
  )
}

export default PageNumberCheckSection
