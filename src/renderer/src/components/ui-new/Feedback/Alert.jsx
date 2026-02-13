import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { X, AlertCircle, CheckCircle2, AlertTriangle, Info } from 'lucide-react'
import styles from './Alert.module.css'

/**
 * Alert - 提示框组件
 * @param {Object} props
 * @param {React.ReactNode} props.children - 内容
 * @param {'success'|'warning'|'error'|'info'} [props.type] - 类型
 * @param {string} [props.title] - 标题
 * @param {boolean} [props.closable] - 是否可关闭
 * @param {Function} [props.onClose] - 关闭回调
 * @param {boolean} [props.showIcon] - 是否显示图标
 * @param {string} [props.className] - 额外的类名
 */
function Alert({
  children,
  type = 'info',
  title,
  closable = false,
  onClose,
  showIcon = true,
  className,
  ...rest
}) {
  const alertClasses = classNames(
    styles.alert,
    styles[`alert--${type}`],
    className
  )

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={20} />
      case 'warning':
        return <AlertTriangle size={20} />
      case 'error':
        return <AlertCircle size={20} />
      default:
        return <Info size={20} />
    }
  }

  return (
    <div className={alertClasses} role="alert" {...rest}>
      {showIcon && <div className={styles.alert__icon}>{getIcon()}</div>}
      <div className={styles.alert__content}>
        {title && <div className={styles.alert__title}>{title}</div>}
        {children && <div className={styles.alert__message}>{children}</div>}
      </div>
      {closable && (
        <button
          className={styles.alert__close}
          onClick={onClose}
          aria-label="关闭"
        >
          <X size={16} />
        </button>
      )}
    </div>
  )
}

Alert.propTypes = {
  children: PropTypes.node,
  type: PropTypes.oneOf(['success', 'warning', 'error', 'info']),
  title: PropTypes.node,
  closable: PropTypes.bool,
  onClose: PropTypes.func,
  showIcon: PropTypes.bool,
  className: PropTypes.string,
}

export default Alert
