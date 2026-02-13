import React from 'react'
import classNames from 'classnames'
import './OptimizedCard.css'

/**
 * 优化版卡片组件 - 替代 GlowCard
 * 移除 Framer Motion 依赖，使用纯 CSS 实现动画效果
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - 子内容
 * @param {string} [props.className] - 额外的类名
 * @param {'blue'|'cyan'|'purple'|'success'|'warning'|'error'|'default'} [props.accentColor] - 强调色
 * @param {boolean} [props.hoverable] - 是否有悬停效果
 * @param {boolean} [props.animated] - 是否有入场动画
 * @param {boolean} [props.glass] - 是否使用玻璃效果
 * @param {boolean} [props.cornerDecoration] - 是否显示装饰性边角
 */
function OptimizedCard({
  children,
  className,
  accentColor = 'default',
  hoverable = true,
  animated = false,
  glass = false,
  cornerDecoration = false,
  ...rest
}) {
  const cardClasses = classNames(
    'optimized-card',
    `optimized-card--${accentColor}`,
    {
      'optimized-card--hoverable': hoverable,
      'optimized-card--animated': animated,
      'optimized-card--glass': glass,
      'optimized-card--corner': cornerDecoration,
    },
    className
  )

  return (
    <div className={cardClasses} {...rest}>
      {cornerDecoration && (
        <>
          <div className="optimized-card__corner optimized-card__corner--tl" />
          <div className="optimized-card__corner optimized-card__corner--tr" />
          <div className="optimized-card__corner optimized-card__corner--bl" />
          <div className="optimized-card__corner optimized-card__corner--br" />
        </>
      )}
      <div className="optimized-card__content">{children}</div>
    </div>
  )
}

export default OptimizedCard
