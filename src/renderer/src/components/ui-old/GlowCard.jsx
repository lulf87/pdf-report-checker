import React from 'react'
import { motion } from 'framer-motion'
import classNames from 'classnames'
import './GlowCard.css'

/**
 * 霓虹发光卡片容器组件
 * @param {Object} props
 * @param {React.ReactNode} props.children - 子内容
 * @param {string} [props.className] - 额外的类名
 * @param {'blue'|'cyan'|'purple'|'success'|'warning'|'error'} [props.glowColor] - 发光颜色
 * @param {boolean} [props.hoverable] - 是否有悬停效果
 * @param {boolean} [props.animated] - 是否有入场动画
 * @param {number} [props.delay] - 动画延迟时间(ms)
 */
function GlowCard({
  children,
  className,
  glowColor = 'blue',
  hoverable = true,
  animated = true,
  delay = 0,
  ...rest
}) {
  const cardClasses = classNames(
    'glow-card',
    `glow-card--${glowColor}`,
    {
      'glow-card--hoverable': hoverable,
    },
    className
  )

  const motionProps = animated
    ? {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.5, delay: delay / 1000 },
      }
    : {}

  return (
    <motion.div className={cardClasses} {...motionProps} {...rest}>
      {/* 装饰性边角 */}
      <div className="glow-card__corner glow-card__corner--tl" />
      <div className="glow-card__corner glow-card__corner--tr" />
      <div className="glow-card__corner glow-card__corner--bl" />
      <div className="glow-card__corner glow-card__corner--br" />

      {/* 内容区域 */}
      <div className="glow-card__content">{children}</div>
    </motion.div>
  )
}

export default GlowCard
