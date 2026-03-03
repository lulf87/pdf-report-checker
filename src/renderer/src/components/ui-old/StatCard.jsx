import React from 'react'
import { motion } from 'framer-motion'
import CountUp from 'react-countup'
import classNames from 'classnames'
import './StatCard.css'

/**
 * 数据统计卡片组件 - 带数字跳动动画
 * @param {Object} props
 * @param {string} props.title - 标题
 * @param {string|number} props.value - 数值
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {'success'|'error'|'warning'|'info'|'blue'|'cyan'|'purple'} [props.type] - 类型/颜色
 * @param {string} [props.suffix] - 后缀（如 '%'）
 * @param {string} [props.prefix] - 前缀
 * @param {number} [props.decimals] - 小数位数
 * @param {boolean} [props.animated] - 是否有入场动画
 * @param {number} [props.delay] - 动画延迟时间(ms)
 * @param {string} [props.className] - 额外的类名
 */
function StatCard({
  title,
  value,
  icon,
  type = 'blue',
  suffix = '',
  prefix = '',
  decimals = 0,
  animated = true,
  delay = 0,
  className,
  ...rest
}) {
  const cardClasses = classNames(
    'stat-card',
    `stat-card--${type}`,
    className
  )

  // 解析数值
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0
  const isPercentage = typeof value === 'string' && value.includes('%')

  const motionProps = animated
    ? {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.5, delay: delay / 1000 },
      }
    : {}

  return (
    <motion.div className={cardClasses} {...motionProps} {...rest}>
      {/* 背景装饰 */}
      <div className="stat-card__bg">
        <div className="stat-card__bg-pattern" />
      </div>

      {/* 图标 */}
      {icon && (
        <div className="stat-card__icon">
          {icon}
        </div>
      )}

      {/* 数值 */}
      <div className="stat-card__value">
        {prefix}
        <CountUp
          end={numericValue}
          duration={1.5}
          decimals={isPercentage ? 1 : decimals}
          separator=","
        />
        {suffix || (isPercentage ? '%' : '')}
      </div>

      {/* 标题 */}
      <div className="stat-card__title">{title}</div>

      {/* 底部发光条 */}
      <div className="stat-card__glow-bar" />
    </motion.div>
  )
}

export default StatCard
