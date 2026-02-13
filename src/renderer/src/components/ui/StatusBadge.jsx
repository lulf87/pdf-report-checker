import React from 'react'
import { motion } from 'framer-motion'
import classNames from 'classnames'
import './StatusBadge.css'

/**
 * 状态徽章组件
 * @param {Object} props
 * @param {'success'|'error'|'warning'|'info'|'blue'|'cyan'|'purple'} [props.status] - 状态类型
 * @param {string} [props.text] - 显示文本
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {'sm'|'md'|'lg'} [props.size] - 尺寸
 * @param {boolean} [props.pulse] - 是否有脉冲动画
 * @param {boolean} [props.outline] - 是否为轮廓样式
 * @param {string} [props.className] - 额外的类名
 */
function StatusBadge({
  status = 'info',
  text,
  icon,
  size = 'md',
  pulse = false,
  outline = false,
  className,
  ...rest
}) {
  const badgeClasses = classNames(
    'status-badge',
    `status-badge--${status}`,
    `status-badge--${size}`,
    {
      'status-badge--pulse': pulse,
      'status-badge--outline': outline,
    },
    className
  )

  return (
    <motion.span
      className={badgeClasses}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      {...rest}
    >
      {/* 状态指示灯 */}
      <span className="status-badge__dot" />

      {/* 图标 */}
      {icon && <span className="status-badge__icon">{icon}</span>}

      {/* 文本 */}
      {text && <span className="status-badge__text">{text}</span>}
    </motion.span>
  )
}

export default StatusBadge
