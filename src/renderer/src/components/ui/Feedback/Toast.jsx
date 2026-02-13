import React, { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import styles from './Toast.module.css'

/**
 * Toast - 轻提示组件
 * @param {Object} props
 * @param {React.ReactNode} props.children - 内容
 * @param {'success'|'warning'|'error'|'info'} [props.type] - 类型
 * @param {number} [props.duration] - 自动关闭时间(ms)，0表示不自动关闭
 * @param {Function} [props.onClose] - 关闭回调
 * @param {boolean} [props.visible] - 是否可见
 * @param {string} [props.className] - 额外的类名
 */
function Toast({
  children,
  type = 'info',
  duration = 3000,
  onClose,
  visible = true,
  className,
  ...rest
}) {
  const [isVisible, setIsVisible] = useState(visible)

  useEffect(() => {
    setIsVisible(visible)
  }, [visible])

  useEffect(() => {
    if (duration > 0 && isVisible) {
      const timer = setTimeout(() => {
        handleClose()
      }, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, isVisible])

  const handleClose = () => {
    setIsVisible(false)
    setTimeout(() => {
      onClose?.()
    }, 200)
  }

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={18} />
      case 'warning':
        return <AlertTriangle size={18} />
      case 'error':
        return <AlertCircle size={18} />
      default:
        return <Info size={18} />
    }
  }

  const toastClasses = classNames(
    styles.toast,
    styles[`toast--${type}`],
    {
      [styles['toast--visible']]: isVisible,
      [styles['toast--hidden']]: !isVisible,
    },
    className
  )

  return (
    <div className={toastClasses} role="alert" {...rest}>
      <div className={styles.toast__icon}>{getIcon()}</div>
      <div className={styles.toast__content}>{children}</div>
      <button
        className={styles.toast__close}
        onClick={handleClose}
        aria-label="关闭"
      >
        <X size={14} />
      </button>
    </div>
  )
}

Toast.propTypes = {
  children: PropTypes.node,
  type: PropTypes.oneOf(['success', 'warning', 'error', 'info']),
  duration: PropTypes.number,
  onClose: PropTypes.func,
  visible: PropTypes.bool,
  className: PropTypes.string,
}

export default Toast
