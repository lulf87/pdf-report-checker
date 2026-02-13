import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { Loader2 } from 'lucide-react'
import styles from './Button.module.css'

/**
 * Button 按钮组件
 * @param {Object} props
 * @param {React.ReactNode} props.children - 按钮内容
 * @param {'primary'|'secondary'|'danger'|'ghost'|'icon'} [props.variant] - 按钮变体
 * @param {'sm'|'md'|'lg'} [props.size] - 按钮尺寸
 * @param {boolean} [props.disabled] - 是否禁用
 * @param {boolean} [props.loading] - 是否加载中
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {'left'|'right'} [props.iconPosition] - 图标位置
 * @param {Function} [props.onClick] - 点击事件
 * @param {string} [props.className] - 额外的类名
 * @param {string} [props.type] - 按钮类型
 */
function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
  onClick,
  className,
  type = 'button',
  ...rest
}) {
  const buttonClasses = classNames(
    styles.button,
    styles[`button--${variant}`],
    styles[`button--${size}`],
    {
      [styles['button--disabled']]: disabled || loading,
      [styles['button--loading']]: loading,
      [styles['button--with-icon']]: icon && !loading,
      [styles['button--icon-only']]: variant === 'icon',
    },
    className
  )

  const handleClick = (e) => {
    if (disabled || loading) return
    onClick?.(e)
  }

  return (
    <button
      type={type}
      className={buttonClasses}
      onClick={handleClick}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && (
        <span className={styles.button__loader}>
          <Loader2 size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />
        </span>
      )}
      {!loading && icon && iconPosition === 'left' && (
        <span className={styles.button__icon}>{icon}</span>
      )}
      {children && <span className={styles.button__content}>{children}</span>}
      {!loading && icon && iconPosition === 'right' && (
        <span className={styles.button__icon}>{icon}</span>
      )}
    </button>
  )
}

Button.propTypes = {
  children: PropTypes.node,
  variant: PropTypes.oneOf(['primary', 'secondary', 'danger', 'ghost', 'icon']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  icon: PropTypes.node,
  iconPosition: PropTypes.oneOf(['left', 'right']),
  onClick: PropTypes.func,
  className: PropTypes.string,
  type: PropTypes.string,
}

export default Button
