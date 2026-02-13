import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import styles from './StatCard.module.css'

/**
 * StatCard - 统计卡片
 * @param {Object} props
 * @param {string} props.title - 标题
 * @param {string|number} props.value - 数值
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {'success'|'warning'|'error'|'info'|'blue'|'cyan'|'purple'} [props.type] - 类型/颜色
 * @param {string} [props.suffix] - 后缀
 * @param {string} [props.prefix] - 前缀
 * @param {number} [props.trend] - 趋势值(正数上升，负数下降)
 * @param {string} [props.trendLabel] - 趋势标签
 * @param {string} [props.className] - 额外的类名
 */
function StatCard({
  title,
  value,
  icon,
  type = 'blue',
  suffix = '',
  prefix = '',
  trend,
  trendLabel,
  className,
  ...rest
}) {
  const cardClasses = classNames(
    styles.statCard,
    styles[`statCard--${type}`],
    className
  )

  const formatValue = (val) => {
    if (typeof val === 'number') {
      return val.toLocaleString()
    }
    return val
  }

  const getTrendIcon = () => {
    if (trend > 0) return <TrendingUp size={14} />
    if (trend < 0) return <TrendingDown size={14} />
    return <Minus size={14} />
  }

  const getTrendClass = () => {
    if (trend > 0) return styles['statCard__trend--up']
    if (trend < 0) return styles['statCard__trend--down']
    return styles['statCard__trend--neutral']
  }

  return (
    <div className={cardClasses} {...rest}>
      <div className={styles.statCard__header}>
        {icon && <div className={styles.statCard__icon}>{icon}</div>}
        <span className={styles.statCard__title}>{title}</span>
      </div>

      <div className={styles.statCard__value}>
        {prefix && <span className={styles.statCard__prefix}>{prefix}</span>}
        <span className={styles.statCard__number}>{formatValue(value)}</span>
        {suffix && <span className={styles.statCard__suffix}>{suffix}</span>}
      </div>

      {trend !== undefined && (
        <div className={classNames(styles.statCard__trend, getTrendClass())}>
          {getTrendIcon()}
          <span>{Math.abs(trend)}%</span>
          {trendLabel && <span className={styles.statCard__trendLabel}>{trendLabel}</span>}
        </div>
      )}

      <div className={styles.statCard__glow} />
    </div>
  )
}

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.node,
  type: PropTypes.oneOf(['success', 'warning', 'error', 'info', 'blue', 'cyan', 'purple']),
  suffix: PropTypes.string,
  prefix: PropTypes.string,
  trend: PropTypes.number,
  trendLabel: PropTypes.string,
  className: PropTypes.string,
}

export default StatCard
