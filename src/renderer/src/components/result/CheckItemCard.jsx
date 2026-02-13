/**
 * CheckItemCard - 单项核对卡片组件
 * 显示核对项编号、名称、状态、错误/警告计数
 * 科技感数据大屏设计系统
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
export default function CheckItemCard({
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
  const totalIssues = errorCount + warningCount

  const handleToggle = () => {
    if (hasDetails) {
      setIsExpanded(!isExpanded)
    }
  }

  return (
    <motion.div
      className={`${styles.checkItemCard} ${styles[config.className]} ${isExpanded ? styles.expanded : ''}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.34, 1.56, 0.64, 1] }}
      whileHover={hasDetails ? { scale: 1.005 } : {}}
    >
      {/* 头部区域 */}
      <div
        className={`${styles.cardHeader} ${hasDetails ? styles.clickable : ''}`}
        onClick={handleToggle}
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

      {/* 详情区域（可折叠） */}
      <AnimatePresence>
        {isExpanded && hasDetails && (
          <motion.div
            className={styles.detailsContainer}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              height: { duration: 0.3, ease: [0.34, 1.56, 0.64, 1] },
              opacity: { duration: 0.2 }
            }}
          >
            <div className={styles.detailsContent}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
