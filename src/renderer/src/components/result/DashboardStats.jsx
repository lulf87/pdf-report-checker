/**
 * DashboardStats - 统计仪表盘组件 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React, { useMemo } from 'react'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  AppstoreOutlined,
  PieChartOutlined,
} from '@ant-design/icons'
import styles from './DashboardStats.module.css'

/**
 * 统计卡片组件
 */
function StatCard({ title, value, suffix, icon, type }) {
  return (
    <div className={`${styles.statCard} ${styles[type]}`}>
      <div className={styles.statIcon}>{icon}</div>
      <div className={styles.statContent}>
        <div className={styles.statValue}>
          {value}
          {suffix && <span className={styles.statSuffix}>{suffix}</span>}
        </div>
        <div className={styles.statTitle}>{title}</div>
      </div>
    </div>
  )
}

/**
 * 环形进度条组件
 */
function CircularProgress({ percentage, size = 120 }) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  const colorClass = percentage >= 80 ? styles.success : percentage >= 60 ? styles.warning : styles.error

  return (
    <div className={styles.circularProgress} style={{ width: size, height: size }}>
      <svg width={size} height={size} className={styles.circularSvg}>
        <circle
          className={styles.circularBg}
          cx={size / 2}
          cy={size / 2}
          r={radius}
        />
        <circle
          className={`${styles.circularFill} ${colorClass}`}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          style={{ strokeDashoffset }}
        />
      </svg>
      <div className={styles.circularText}>
        <span className={styles.circularValue}>{percentage.toFixed(1)}%</span>
      </div>
    </div>
  )
}

/**
 * 统计仪表盘组件
 * @param {Object} props
 * @param {Object} props.result - 核对结果对象
 */
function DashboardStats({ result }) {
  if (!result) return null

  const {
    total_components = 0,
    passed_components = 0,
    failed_components = 0,
  } = result

  const passRate = total_components > 0
    ? (passed_components / total_components) * 100
    : 0

  // 统计数据
  const stats = useMemo(() => [
    {
      title: '总字段',
      value: total_components,
      icon: <AppstoreOutlined />,
      type: 'blue',
    },
    {
      title: '通过',
      value: passed_components,
      icon: <CheckCircleOutlined />,
      type: 'success',
    },
    {
      title: '失败',
      value: failed_components,
      icon: <CloseCircleOutlined />,
      type: 'error',
    },
    {
      title: '通过率',
      value: passRate.toFixed(1),
      suffix: '%',
      icon: <PieChartOutlined />,
      type: passRate >= 80 ? 'success' : passRate >= 60 ? 'warning' : 'error',
    },
  ], [total_components, passed_components, failed_components, passRate])

  const passRateLabel = useMemo(() => {
    if (passRate >= 90) return '优秀'
    if (passRate >= 80) return '良好'
    if (passRate >= 60) return '一般'
    return '需要关注'
  }, [passRate])

  return (
    <div className={styles.dashboardStats}>
      {/* 左侧：统计卡片网格 */}
      <div className={styles.statsGrid}>
        {stats.map((stat, index) => (
          <StatCard key={index} {...stat} />
        ))}
      </div>

      {/* 右侧：环形进度图 */}
      <div className={styles.progressSection}>
        <CircularProgress percentage={passRate} />
        <div className={styles.progressLabel}>
          <span className={styles.progressTitle}>总体通过率</span>
          <span className={styles.progressDesc}>{passRateLabel}</span>
        </div>
      </div>
    </div>
  )
}

export default DashboardStats
