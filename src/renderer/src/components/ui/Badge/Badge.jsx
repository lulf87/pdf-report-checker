import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './Badge.module.css'

/**
 * Badge - 徽章组件
 * @param {Object} props
 * @param {React.ReactNode} [props.children] - 徽章内容
 * @param {'success'|'warning'|'error'|'info'|'neutral'|'blue'|'cyan'|'purple'} [props.variant] - 变体
 * @param {'sm'|'md'|'lg'} [props.size] - 尺寸
 * @param {boolean} [props.dot] - 是否显示为点状
 * @param {boolean} [props.pulse] - 是否有脉冲动画
 * @param {boolean} [props.outline] - 是否为轮廓样式
 * @param {string} [props.className] - 额外的类名
 */
function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  pulse = false,
  outline = false,
  className,
  ...rest
}) {
  const badgeClasses = classNames(
    styles.badge,
    styles[`badge--${variant}`],
    styles[`badge--${size}`],
    {
      [styles['badge--dot']]: dot,
      [styles['badge--pulse']]: pulse,
      [styles['badge--outline']]: outline,
      [styles['badge--with-text']]: !dot && children,
    },
    className
  )

  if (dot) {
    return <span className={badgeClasses} {...rest} />
  }

  return (
    <span className={badgeClasses} {...rest}>
      {children}
    </span>
  )
}

Badge.propTypes = {
  children: PropTypes.node,
  variant: PropTypes.oneOf(['success', 'warning', 'error', 'info', 'neutral', 'blue', 'cyan', 'purple']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  dot: PropTypes.bool,
  pulse: PropTypes.bool,
  outline: PropTypes.bool,
  className: PropTypes.string,
}

export default Badge
