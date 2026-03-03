import React, { useId } from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { CheckCircle2, XCircle, AlertCircle, ChevronRight } from 'lucide-react'
import styles from './CheckItemCard.module.css'

/**
 * CheckItemCard - 核对项卡片
 * @param {Object} props
 * @param {string} props.title - 标题
 * @param {string} [props.description] - 描述
 * @param {'success'|'error'|'warning'|'pending'} [props.status] - 状态
 * @param {string} [props.statusText] - 状态文本
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {Function} [props.onClick] - 点击事件
 * @param {boolean} [props.expandable] - 是否可展开
 * @param {boolean} [props.expanded] - 是否已展开
 * @param {React.ReactNode} [props.children] - 展开内容
 * @param {string} [props.className] - 额外的类名
 */
function CheckItemCard({
  title,
  description,
  status = 'pending',
  statusText,
  icon,
  onClick,
  expandable = false,
  expanded = false,
  children,
  className,
  ...rest
}) {
  const contentId = useId()
  const cardClasses = classNames(
    styles.checkItemCard,
    styles[`checkItemCard--${status}`],
    {
      [styles['checkItemCard--clickable']]: onClick || expandable,
      [styles['checkItemCard--expanded']]: expanded,
    },
    className
  )

  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className={classNames(styles.checkItemCard__statusIcon, styles['checkItemCard__statusIcon--success'])} />
      case 'error':
        return <XCircle className={classNames(styles.checkItemCard__statusIcon, styles['checkItemCard__statusIcon--error'])} />
      case 'warning':
        return <AlertCircle className={classNames(styles.checkItemCard__statusIcon, styles['checkItemCard__statusIcon--warning'])} />
      default:
        return <div className={classNames(styles.checkItemCard__statusIcon, styles['checkItemCard__statusIcon--pending'])} />
    }
  }

  const getDefaultStatusText = () => {
    switch (status) {
      case 'success':
        return '通过'
      case 'error':
        return '未通过'
      case 'warning':
        return '警告'
      default:
        return '待检查'
    }
  }

  const handleClick = () => {
    if (onClick) onClick()
  }

  return (
    <div className={cardClasses} {...rest}>
      <div
        className={styles.checkItemCard__header}
        onClick={handleClick}
        role={onClick || expandable ? 'button' : undefined}
        tabIndex={onClick || expandable ? 0 : undefined}
        aria-expanded={expandable ? expanded : undefined}
        aria-controls={expandable ? contentId : undefined}
      >
        <div className={styles.checkItemCard__main}>
          {icon && <div className={styles.checkItemCard__icon}>{icon}</div>}
          <div className={styles.checkItemCard__info}>
            <h4 className={styles.checkItemCard__title}>{title}</h4>
            {description && <p className={styles.checkItemCard__description}>{description}</p>}
          </div>
        </div>

        <div className={styles.checkItemCard__meta}>
          <span className={classNames(styles.checkItemCard__status, styles[`checkItemCard__status--${status}`])}>
            {statusText || getDefaultStatusText()}
          </span>
          {getStatusIcon()}
          {expandable && (
            <ChevronRight
              className={classNames(styles.checkItemCard__arrow, {
                [styles['checkItemCard__arrow--expanded']]: expanded,
              })}
            />
          )}
        </div>
      </div>

      {expandable && expanded && children && (
        <div id={contentId} className={styles.checkItemCard__content}>{children}</div>
      )}
    </div>
  )
}

CheckItemCard.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  status: PropTypes.oneOf(['success', 'error', 'warning', 'pending']),
  statusText: PropTypes.string,
  icon: PropTypes.node,
  onClick: PropTypes.func,
  expandable: PropTypes.bool,
  expanded: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
}

export default CheckItemCard
