import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import classNames from 'classnames'
import styles from './styles.module.css'

/**
 * 单个统计卡片组件 - 带有数字动画效果
 * @param {Object} props
 * @param {string} props.title - 标题
 * @param {string|number} props.value - 数值
 * @param {React.ReactNode} props.icon - 图标
 * @param {string} props.color - 颜色主题: 'medical' | 'pass' | 'fail'
 * @param {string} [props.suffix] - 后缀
 */
function StatCard({ title, value, icon, color, suffix = '' }) {
  const [displayValue, setDisplayValue] = useState(0)
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0

  // 数字动画
  useEffect(() => {
    const duration = 1000
    const steps = 30
    const stepValue = numericValue / steps
    let current = 0

    const timer = setInterval(() => {
      current += stepValue
      if (current >= numericValue) {
        setDisplayValue(numericValue)
        clearInterval(timer)
      } else {
        setDisplayValue(Math.floor(current * 10) / 10)
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [numericValue])

  const colorStyles = {
    medical: 'from-blue-500 to-blue-600',
    pass: 'from-emerald-500 to-emerald-600',
    fail: 'from-red-500 to-red-600',
  }

  return (
    <motion.div
      className={classNames(styles.statCard, styles[color])}
      whileHover={{ y: -4, boxShadow: '0 8px 25px -5px rgba(0, 0, 0, 0.1)' }}
      transition={{ duration: 0.3 }}
    >
      {/* 背景图标 */}
      <div className={classNames(styles.statCardIcon, styles[color])}>
        {icon}
      </div>

      {/* 数值 */}
      <motion.div
        className={styles.statCardValue}
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {typeof value === 'string' && value.includes('%')
          ? `${displayValue.toFixed(1)}%`
          : Math.floor(displayValue)}
        {suffix}
      </motion.div>

      {/* 标题 */}
      <div className={styles.statCardTitle}>{title}</div>

      {/* 装饰性渐变条 */}
      <div className={classNames(
        'absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r',
        colorStyles[color] || colorStyles.medical
      )} />
    </motion.div>
  )
}

export default StatCard
