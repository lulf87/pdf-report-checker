/**
 * CheckGroupCard - 核对分组卡片组件 (重构版)
 * 显示分组名称、图标、通过进度
 * 支持折叠/展开功能
 * 使用新的设计系统和CSS变量
 */

import React, { useMemo, useCallback, memo } from 'react'
import { CheckCircleOutlined, DownOutlined, RightOutlined } from '@ant-design/icons'
import CheckItemCard from './CheckItemCard'
import styles from './CheckGroupCard.module.css'

/**
 * 进度环组件
 */
const ProgressRing = memo(function ProgressRing({ passRate, colorClass }) {
  return (
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
          className={`${styles.circle} ${colorClass}`}
          strokeDasharray={`${passRate}, 100`}
          d="M18 2.0845
            a 15.9155 15.9155 0 0 1 0 31.831
            a 15.9155 15.9155 0 0 1 0 -31.831"
        />
      </svg>
      <span className={styles.progressPercentage}>{Math.round(passRate)}%</span>
    </div>
  )
})

/**
 * 进度条组件
 */
const ProgressBar = memo(function ProgressBar({ passRate, colorClass }) {
  return (
    <div className={styles.progressBarContainer}>
      <div
        className={`${styles.progressBar} ${colorClass}`}
        style={{ width: `${passRate}%` }}
      />
    </div>
  )
})

/**
 * 分组头部组件
 */
const GroupHeader = memo(function GroupHeader({
  name,
  icon,
  totalItems,
  passedItems,
  failedItems,
  warningItems,
  passRate,
  progressColor,
  isExpanded,
  onToggle
}) {
  const hasIssues = failedItems > 0 || warningItems > 0

  return (
    <div
      className={`${styles.groupHeader} ${styles.clickable}`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onToggle()}
    >
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

      <div className={styles.headerRight}>
        {/* 右侧进度环 */}
        <ProgressRing passRate={passRate} colorClass={progressColor} />

        {/* 展开/折叠指示器 */}
        <div className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}>
          {isExpanded ? <DownOutlined /> : <RightOutlined />}
        </div>
      </div>
    </div>
  )
})

/**
 * CheckGroupCard 组件
 * @param {Object} props
 * @param {string} props.id - 分组ID
 * @param {string} props.name - 分组名称
 * @param {React.ReactNode} props.icon - 分组图标
 * @param {Array} props.items - 核对项列表
 * @param {boolean} props.isExpanded - 是否展开
 * @param {Function} props.onToggle - 切换展开/折叠的回调
 */
function CheckGroupCard({
  id,
  name,
  icon,
  items = [],
  isExpanded = true,
  onToggle
}) {
  // 计算统计信息
  const stats = useMemo(() => {
    const totalItems = items.length
    const passedItems = items.filter(item => item.status === 'pass').length
    const failedItems = items.filter(item => item.status === 'fail').length
    const warningItems = items.filter(item => item.status === 'warning').length
    const passRate = totalItems > 0 ? (passedItems / totalItems) * 100 : 0

    return {
      totalItems,
      passedItems,
      failedItems,
      warningItems,
      passRate,
      hasIssues: failedItems > 0 || warningItems > 0
    }
  }, [items])

  // 根据通过率确定进度条颜色
  const progressColor = useMemo(() => {
    if (stats.passRate === 100) return styles.progressSuccess
    if (stats.passRate >= 60) return styles.progressWarning
    return styles.progressError
  }, [stats.passRate])

  // 根据状态确定分组边框颜色
  const groupStatusClass = useMemo(() => {
    if (stats.failedItems > 0) return styles.groupFail
    if (stats.warningItems > 0) return styles.groupWarning
    if (stats.passedItems === stats.totalItems && stats.totalItems > 0) return styles.groupPass
    return ''
  }, [stats.failedItems, stats.warningItems, stats.passedItems, stats.totalItems])

  // 切换展开状态
  const handleToggle = useCallback(() => {
    onToggle?.(id)
  }, [onToggle, id])

  return (
    <div className={`${styles.checkGroupCard} ${groupStatusClass}`}>
      {/* 分组头部 - 可点击折叠/展开 */}
      <GroupHeader
        name={name}
        icon={icon}
        totalItems={stats.totalItems}
        passedItems={stats.passedItems}
        failedItems={stats.failedItems}
        warningItems={stats.warningItems}
        passRate={stats.passRate}
        progressColor={progressColor}
        isExpanded={isExpanded}
        onToggle={handleToggle}
      />

      {/* 进度条 */}
      <ProgressBar passRate={stats.passRate} colorClass={progressColor} />

      {/* 核对项列表 - 可折叠 */}
      <div className={`${styles.itemsList} ${isExpanded ? styles.expanded : styles.collapsed}`}>
        {items.map((item, index) => (
          <div
            key={item.code}
            className={styles.itemWrapper}
            style={{ animationDelay: `${index * 30}ms` }}
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
          </div>
        ))}
      </div>

      {/* 空状态 */}
      {items.length === 0 && (
        <div className={styles.emptyState}>
          <span className={styles.emptyText}>暂无核对项</span>
        </div>
      )}
    </div>
  )
}

// 使用memo包装，避免不必要的重渲染
export default memo(CheckGroupCard)
