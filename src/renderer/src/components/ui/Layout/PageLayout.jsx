import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './PageLayout.module.css'

/**
 * PageLayout - 页面布局框架
 * @param {Object} props
 * @param {React.ReactNode} [props.header] - 头部内容
 * @param {React.ReactNode} [props.sidebar] - 侧边栏内容
 * @param {React.ReactNode} [props.children] - 主内容
 * @param {React.ReactNode} [props.footer] - 底部内容
 * @param {boolean} [props.fullWidth] - 是否全宽
 * @param {string} [props.className] - 额外的类名
 */
function PageLayout({
  header,
  sidebar,
  children,
  footer,
  fullWidth = false,
  className,
  ...rest
}) {
  const layoutClasses = classNames(
    styles.pageLayout,
    {
      [styles['pageLayout--withSidebar']]: sidebar,
      [styles['pageLayout--fullWidth']]: fullWidth,
    },
    className
  )

  return (
    <div className={layoutClasses} {...rest}>
      {header && <header className={styles.pageLayout__header}>{header}</header>}
      <div className={styles.pageLayout__body}>
        {sidebar && <aside className={styles.pageLayout__sidebar}>{sidebar}</aside>}
        <main className={styles.pageLayout__main}>{children}</main>
      </div>
      {footer && <footer className={styles.pageLayout__footer}>{footer}</footer>}
    </div>
  )
}

PageLayout.propTypes = {
  header: PropTypes.node,
  sidebar: PropTypes.node,
  children: PropTypes.node,
  footer: PropTypes.node,
  fullWidth: PropTypes.bool,
  className: PropTypes.string,
}

export default PageLayout
