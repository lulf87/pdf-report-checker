import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import styles from './GridBackground.module.css'

/**
 * GridBackground - 网格背景组件
 * @param {Object} props
 * @param {'sm'|'md'|'lg'} [props.gridSize] - 网格大小
 * @param {boolean} [props.animated] - 是否有动画
 * @param {string} [props.className] - 额外的类名
 */
function GridBackground({
  gridSize = 'md',
  animated = false,
  className,
  ...rest
}) {
  const gridClasses = classNames(
    styles.gridBackground,
    styles[`gridBackground--${gridSize}`],
    {
      [styles['gridBackground--animated']]: animated,
    },
    className
  )

  return (
    <div
      className={gridClasses}
      aria-hidden="true"
      {...rest}
    >
      <div className={styles.gridBackground__grid} />
    </div>
  )
}

GridBackground.propTypes = {
  gridSize: PropTypes.oneOf(['sm', 'md', 'lg']),
  animated: PropTypes.bool,
  className: PropTypes.string,
}

export default GridBackground
