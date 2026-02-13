import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { Loader2 } from 'lucide-react'
import styles from './Loading.module.css'

/**
 * Loading - 加载状态组件
 * @param {Object} props
 * @param {string} [props.text] - 加载文本
 * @param {'sm'|'md'|'lg'} [props.size] - 尺寸
 * @param {boolean} [props.fullscreen] - 是否全屏
 * @param {boolean} [props.overlay] - 是否显示遮罩
 * @param {string} [props.className] - 额外的类名
 */
function Loading({
  text = '加载中...',
  size = 'md',
  fullscreen = false,
  overlay = false,
  className,
  ...rest
}) {
  const loadingClasses = classNames(
    styles.loading,
    styles[`loading--${size}`],
    {
      [styles['loading--fullscreen']]: fullscreen,
      [styles['loading--overlay']]: overlay,
    },
    className
  )

  const iconSizes = {
    sm: 16,
    md: 24,
    lg: 48,
  }

  return (
    <div className={loadingClasses} {...rest}>
      <div className={styles.loading__content}>
        <Loader2
          size={iconSizes[size]}
          className={styles.loading__spinner}
        />
        {text && <span className={styles.loading__text}>{text}</span>}
      </div>
    </div>
  )
}

Loading.propTypes = {
  text: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  fullscreen: PropTypes.bool,
  overlay: PropTypes.bool,
  className: PropTypes.string,
}

export default Loading
