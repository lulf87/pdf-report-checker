/**
 * CheckGroupCard - 核对分组卡片组件
 * 显示分组名称、图标、通过进度
 * 科技感数据大屏设计系统
 */

import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircleOutlined } from '@ant-design/icons'
import CheckItemCard from './CheckItemCard'
import styles from './CheckGroupCard.module.css'

/**
 * CheckGroupCard 组件
 * @param {Object} props
 * @param {string} props.id - 分组ID
 * @param {string} props.name - 分组名称
 * @param {React.ReactNode} props.icon - 分组图标
 * @param {Array} props.items - 核对项列表
 *   - {string} code - 核对项编号
 *   - {string} name - 核对项名称
 *   - {string} status - 状态
 *   - {string} description - 描述
 *   - {number} errorCount - 错误计数
 *   - {number} warningCount - 警告计数
 *   - {React.ReactNode} details - 详情内容（可选）
 */
export default function CheckGroupCard({ id, name, icon, items = [] }) {
  // 计算统计信息
  const totalItems = items.length
  const passedItems = items.filter(item => item.status === 'pass').length
  const failedItems = items.filter(item => item.status === 'fail').length
  const warningItems = items.filter(item => item.status === 'warning').length

  const passRate = totalItems > 0 ? (passedItems / totalItems) * 100 : 0
  const hasIssues = failedItems > 0 || warningItems > 0

  // 根据通过率确定进度条颜色
  const getProgressColor = () => {
    if (passRate === 100) return styles.progressSuccess
    if (passRate >= 60) return styles.progressWarning
    return styles.progressError
  }

  // 根据状态确定分组边框颜色
  const getGroupStatusClass = () => {
    if (failedItems > 0) return styles.groupFail
    if (warningItems > 0) return styles.groupWarning
    if (passedItems === totalItems && totalItems > 0) return styles.groupPass
    return ''
  }

  return (
    <motion.div
      className={`${styles.checkGroupCard} ${getGroupStatusClass()}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
    >
      {/* 分组头部 */}
      <div className={styles.groupHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.iconWrapper}>
            {icon}
          </div>
          <div className={styles.titleSection}>
            <h3 className={styles.groupName}>{name}</h3>
            <div className={styles.progressText}>
              <CheckCircleOutlined className={styles.progressIcon} />
              <span>{passedItems}/{totalItems} 通过</span>
              {hasIssues && (
                <span className={styles.issueSummary}>
                  {failedItems > 0 && ` · ${failedItems} 失败`}
                  {warningItems > 0 && ` · ${warningItems} 警告`}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 右侧进度环 */}
        <div className={styles.progressRing}>
          <svg viewBox="0 0 36 36" className={styles.circularChart}>
            {/* 背景圆环 */}
            <path
              className={styles.circleBg}
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            {/* 进度圆环 */}
            <path
              className={`${styles.circle} ${getProgressColor()}`}
              strokeDasharray={`${passRate}, 100`}
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <span className={styles.progressPercentage}>{Math.round(passRate)}%</span>
        </div>
      </div>

      {/* 进度条 */}
      <div className={styles.progressBarContainer}>
        <motion.div
          className={`${styles.progressBar} ${getProgressColor()}`}
          initial={{ width: 0 }}
          animate={{ width: `${passRate}%` }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.34, 1.56, 0.64, 1] }}
        />
      </div>

      {/* 核对项列表 */}
      <div className={styles.itemsList}>
        {items.map((item, index) => (
          <motion.div
            key={item.code}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: 0.3,
              delay: index * 0.05,
              ease: [0.34, 1.56, 0.64, 1]
            }}
          >
            <CheckItemCard
              code={item.code}
              name={item.name}
              status={item.status}
              description={item.description}
              errorCount={item.errorCount}
              warningCount={item.warningCount}
              defaultExpanded={item.defaultExpanded}
            >
              {item.details}
            </CheckItemCard>
          </motion.div>
        ))}
      </div>

      {/* 空状态 */}
      {items.length === 0 && (
        <div className={styles.emptyState}>
          <span className={styles.emptyText}>暂无核对项</span>
        </div>
      )}
    </motion.div>
  )
}
