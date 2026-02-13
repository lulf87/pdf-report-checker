import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './Section.module.css'

/**
 * Section - 内容区块
 * @param {Object} props
 * @param {React.ReactNode} props.children - 内容
 * @param {string} [props.title] - 标题
 * @param {React.ReactNode} [props.extra] - 额外操作
 * @param {boolean} [props.bordered] - 是否有边框
 * @param {boolean} [props.shadow] - 是否有阴影
 * @param {'sm'|'md'|'lg'} [props.padding] - 内边距
 * @param {string} [props.className] - 额外的类名
 */
function Section({
  children,
  title,
  extra,
  bordered = true,
  shadow = true,
  padding = 'md',
  className,
  ...rest
}) {
  const sectionClasses = classNames(
    styles.section,
    {
      [styles['section--bordered']]: bordered,
      [styles['section--shadow']]: shadow,
      [styles[`section--padding-${padding}`]]: padding,
    },
    className
  )

  return (
    <section className={sectionClasses} {...rest}>
      {(title || extra) && (
        <div className={styles.section__header}>
          {title && <h2 className={styles.section__title}>{title}</h2>}
          {extra && <div className={styles.section__extra}>{extra}</div>}
        </div>
      )}
      <div className={styles.section__content}>{children}</div>
    </section>
  )
}

Section.propTypes = {
  children: PropTypes.node,
  title: PropTypes.node,
  extra: PropTypes.node,
  bordered: PropTypes.bool,
  shadow: PropTypes.bool,
  padding: PropTypes.oneOf(['sm', 'md', 'lg']),
  className: PropTypes.string,
}

export default Section
