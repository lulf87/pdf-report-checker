import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './ProgressBar.module.css'

/**
 * ProgressBar - 进度条组件
 * @param {Object} props
 * @param {number} props.percentage - 进度百分比 (0-100)
 * @param {'sm'|'md'|'lg'} [props.size] - 尺寸
 * @param {'blue'|'cyan'|'purple'|'success'|'warning'|'error'} [props.color] - 颜色
 * @param {boolean} [props.showLabel] - 是否显示百分比标签
 * @param {boolean} [props.striped] - 是否显示条纹
 * @param {boolean} [props.animated] - 条纹是否动画
 * @param {string} [props.className] - 额外的类名
 */
function ProgressBar({
  percentage = 0,
  size = 'md',
  color = 'blue',
  showLabel = true,
  striped = false,
  animated = false,
  className,
  ...rest
}) {
  const safePercentage = Math.max(0, Math.min(100, percentage))

  const progressClasses = classNames(
    styles.progressBar,
    styles[`progressBar--${size}`],
    className
  )

  const fillClasses = classNames(
    styles.progressBar__fill,
    styles[`progressBar__fill--${color}`],
    {
      [styles['progressBar__fill--striped']]: striped,
      [styles['progressBar__fill--animated']]: animated,
    }
  )

  return (
    <div className={progressClasses} {...rest}>
      <div className={styles.progressBar__track}>
        <div
          className={fillClasses}
          style={{ width: `${safePercentage}%` }}
          role="progressbar"
          aria-valuenow={safePercentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {showLabel && (
        <span className={styles.progressBar__label}>{Math.round(safePercentage)}%</span>
      )}
    </div>
  )
}

ProgressBar.propTypes = {
  percentage: PropTypes.number,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  color: PropTypes.oneOf(['blue', 'cyan', 'purple', 'success', 'warning', 'error']),
  showLabel: PropTypes.bool,
  striped: PropTypes.bool,
  animated: PropTypes.bool,
  className: PropTypes.string,
}

export default ProgressBar
