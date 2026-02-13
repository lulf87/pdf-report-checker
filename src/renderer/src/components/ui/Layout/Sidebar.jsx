import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { ChevronRight } from 'lucide-react'
import styles from './Sidebar.module.css'

/**
 * Sidebar - 侧边栏组件
 * @param {Object} props
 * @param {Array} props.menuItems - 菜单项 [{ key, icon, label, children }]
 * @param {string} [props.activeKey] - 当前激活的key
 * @param {Function} [props.onSelect] - 选择回调
 * @param {string} [props.title] - 标题
 * @param {React.ReactNode} [props.footer] - 底部内容
 * @param {boolean} [props.collapsed] - 是否折叠
 * @param {Function} [props.onCollapse] - 折叠回调
 * @param {string} [props.className] - 额外的类名
 */
function Sidebar({
  menuItems = [],
  activeKey,
  onSelect,
  title,
  footer,
  collapsed = false,
  onCollapse,
  className,
  ...rest
}) {
  const [openKeys, setOpenKeys] = React.useState([])

  const sidebarClasses = classNames(
    styles.sidebar,
    {
      [styles['sidebar--collapsed']]: collapsed,
    },
    className
  )

  const toggleSubmenu = (key) => {
    setOpenKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  const renderMenuItem = (item) => {
    const isActive = item.key === activeKey
    const isOpen = openKeys.includes(item.key)
    const hasChildren = item.children && item.children.length > 0

    const itemClasses = classNames(styles.sidebar__item, {
      [styles['sidebar__item--active']]: isActive,
    })

    return (
      <div key={item.key} className={styles.sidebar__menuItem}>
        <div
          className={itemClasses}
          onClick={() => {
            if (hasChildren) {
              toggleSubmenu(item.key)
            } else {
              onSelect?.(item.key, item)
            }
          }}
        >
          {item.icon && <span className={styles.sidebar__icon}>{item.icon}</span>}
          {!collapsed && (
            <>
              <span className={styles.sidebar__label}>{item.label}</span>
              {hasChildren && (
                <ChevronRight
                  className={classNames(styles.sidebar__arrow, {
                    [styles['sidebar__arrow--open']]: isOpen,
                  })}
                />
              )}
            </>
          )}
        </div>
        {hasChildren && !collapsed && isOpen && (
          <div className={styles.sidebar__submenu}>
            {item.children.map((child) => (
              <div
                key={child.key}
                className={classNames(styles.sidebar__submenuItem, {
                  [styles['sidebar__submenuItem--active']]: child.key === activeKey,
                })}
                onClick={() => onSelect?.(child.key, child)}
              >
                {child.icon && <span className={styles.sidebar__icon}>{child.icon}</span>}
                <span className={styles.sidebar__label}>{child.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <aside className={sidebarClasses} {...rest}>
      {title && (
        <div className={styles.sidebar__header}>
          {!collapsed && <h3 className={styles.sidebar__title}>{title}</h3>}
          {onCollapse && (
            <button
              className={styles.sidebar__collapseBtn}
              onClick={() => onCollapse?.(!collapsed)}
              aria-label={collapsed ? '展开' : '折叠'}
            >
              <ChevronRight
                className={classNames(styles.sidebar__collapseIcon, {
                  [styles['sidebar__collapseIcon--collapsed']]: collapsed,
                })}
              />
            </button>
          )}
        </div>
      )}
      <nav className={styles.sidebar__menu}>{menuItems.map(renderMenuItem)}</nav>
      {footer && <div className={styles.sidebar__footer}>{footer}</div>}
    </aside>
  )
}

Sidebar.propTypes = {
  menuItems: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      icon: PropTypes.node,
      label: PropTypes.node.isRequired,
      children: PropTypes.array,
    })
  ),
  activeKey: PropTypes.string,
  onSelect: PropTypes.func,
  title: PropTypes.node,
  footer: PropTypes.node,
  collapsed: PropTypes.bool,
  onCollapse: PropTypes.func,
  className: PropTypes.string,
}

export default Sidebar
