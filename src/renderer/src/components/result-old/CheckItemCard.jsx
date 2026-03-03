/**
 * CheckItemCard - 单项核对卡片组件 (高性能优化版)
 * 显示核对项编号、名称、状态、错误/警告计数
 * 科技感数据大屏设计系统
 */

import React, { useState, useCallback, memo } from 'react'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  MinusCircleOutlined,
  RightOutlined,
  DownOutlined
} from '@ant-design/icons'
import styles from './CheckItemCard.module.css'

/**
 * 状态配置映射
 */
const statusConfig = {
  pass: {
    icon: <CheckCircleOutlined />,
    label: '通过',
    className: 'pass',
    glowClass: 'glowPass'
  },
  fail: {
    icon: <CloseCircleOutlined />,
    label: '失败',
    className: 'fail',
    glowClass: 'glowFail'
  },
  warning: {
    icon: <WarningOutlined />,
    label: '警告',
    className: 'warning',
    glowClass: 'glowWarning'
  },
  skip: {
    icon: <MinusCircleOutlined />,
    label: '跳过',
    className: 'skip',
    glowClass: 'glowSkip'
  }
}

/**
 * 卡片头部组件
 */
const CardHeader = memo(function CardHeader({
  code,
  name,
  description,
  status,
  errorCount,
  warningCount,
  isExpanded,
  hasDetails,
  onToggle
}) {
  const config = statusConfig[status] || statusConfig.pass
  const totalIssues = errorCount + warningCount

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onToggle()
    }
  }, [onToggle])

  return (
    <div
      className={`${styles.cardHeader} ${hasDetails ? styles.clickable : ''}`}
      onClick={onToggle}
      onKeyDown={handleKeyDown}
      role={hasDetails ? 'button' : undefined}
      tabIndex={hasDetails ? 0 : undefined}
      aria-expanded={hasDetails ? isExpanded : undefined}
    >
      {/* 左侧：编号和图标 */}
      <div className={styles.headerLeft}>
        <div className={`${styles.codeBadge} ${styles[config.className]}`}>
          {code}
        </div>
        <div className={`${styles.statusIcon} ${styles[config.className]}`}>
          {config.icon}
        </div>
      </div>

      {/* 中间：名称和描述 */}
      <div className={styles.headerCenter}>
        <div className={styles.nameRow}>
          <span className={styles.itemName}>{name}</span>
          {totalIssues > 0 && (
            <div className={styles.badgeGroup}>
              {errorCount > 0 && (
                <span className={`${styles.countBadge} ${styles.errorBadge}`}>
                  {errorCount} 错误
                </span>
              )}
              {warningCount > 0 && (
                <span className={`${styles.countBadge} ${styles.warningBadge}`}>
                  {warningCount} 警告
                </span>
              )}
            </div>
          )}
        </div>
        {description && (
          <div className={styles.description}>{description}</div>
        )}
      </div>

      {/* 右侧：展开箭头 */}
      {hasDetails && (
        <div className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}>
          {isExpanded ? <DownOutlined /> : <RightOutlined />}
        </div>
      )}
    </div>
  )
})

/**
 * 详情区域组件
 */
const DetailsSection = memo(function DetailsSection({ isExpanded, hasDetails, children }) {
  if (!hasDetails) return null

  return (
    <div
      className={`${styles.detailsContainer} ${isExpanded ? styles.expanded : styles.collapsed}`}
      aria-hidden={!isExpanded}
    >
      <div className={styles.detailsContent}>
        {children}
      </div>
    </div>
  )
})

/**
 * CheckItemCard 组件
 * @param {Object} props
 * @param {string} props.code - 核对项编号 (C01-C11)
 * @param {string} props.name - 核对项名称
 * @param {string} props.status - 状态: pass/fail/warning/skip
 * @param {string} props.description - 描述文本
 * @param {number} props.errorCount - 错误计数
 * @param {number} props.warningCount - 警告计数
 * @param {boolean} props.defaultExpanded - 是否默认展开详情
 * @param {React.ReactNode} props.children - 详情区域内容（可折叠）
 */
function CheckItemCard({
  code,
  name,
  status = 'pass',
  description,
  errorCount = 0,
  warningCount = 0,
  defaultExpanded = false,
  children
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const config = statusConfig[status] || statusConfig.pass

  const hasDetails = Boolean(children)

  const handleToggle = useCallback(() => {
    if (hasDetails) {
      setIsExpanded(prev => !prev)
    }
  }, [hasDetails])

  return (
    <div
      className={`${styles.checkItemCard} ${styles[config.className]} ${isExpanded ? styles.expanded : ''}`}
    >
      {/* 头部区域 */}
      <CardHeader
        code={code}
        name={name}
        description={description}
        status={status}
        errorCount={errorCount}
        warningCount={warningCount}
        isExpanded={isExpanded}
        hasDetails={hasDetails}
        onToggle={handleToggle}
      />

      {/* 详情区域（可折叠）- CSS过渡替代Framer Motion */}
      <DetailsSection isExpanded={isExpanded} hasDetails={hasDetails}>
        {children}
      </DetailsSection>
    </div>
  )
}

// 使用memo包装，避免不必要的重渲染
export default memo(CheckItemCard)
