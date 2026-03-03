import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './GradientBackground.module.css'

/**
 * GradientBackground - 渐变背景组件
 * @param {Object} props
 * @param {'blue'|'cyan'|'purple'|'mixed'} [props.variant] - 渐变变体
 * @param {boolean} [props.animated] - 是否有动画
 * @param {string} [props.className] - 额外的类名
 */
function GradientBackground({
  variant = 'mixed',
  animated = false,
  className,
  ...rest
}) {
  const gradientClasses = classNames(
    styles.gradientBackground,
    styles[`gradientBackground--${variant}`],
    {
      [styles['gradientBackground--animated']]: animated,
    },
    className
  )

  return (
    <div
      className={gradientClasses}
      aria-hidden="true"
      {...rest}
    >
      <div className={styles.gradientBackground__glow1} />
      <div className={styles.gradientBackground__glow2} />
      <div className={styles.gradientBackground__glow3} />
    </div>
  )
}

GradientBackground.propTypes = {
  variant: PropTypes.oneOf(['blue', 'cyan', 'purple', 'mixed']),
  animated: PropTypes.bool,
  className: PropTypes.string,
}

export default GradientBackground
