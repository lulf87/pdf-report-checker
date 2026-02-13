import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import classNames from 'classnames'
import './ProgressBar.css'

/**
 * 环形进度条组件
 * @param {Object} props
 * @param {number} props.percentage - 百分比 (0-100)
 * @param {'sm'|'md'|'lg'|'xl'} [props.size] - 尺寸
 * @param {number} [props.strokeWidth] - 线条宽度
 * @param {'blue'|'cyan'|'purple'|'success'|'warning'|'error'} [props.color] - 颜色
 * @param {boolean} [props.showLabel] - 是否显示百分比标签
 * @param {boolean} [props.animated] - 是否有动画
 * @param {string} [props.className] - 额外的类名
 * @param {React.ReactNode} [props.label] - 自定义标签内容
 */
function ProgressBar({
  percentage = 0,
  size = 'md',
  strokeWidth,
  color = 'blue',
  showLabel = true,
  animated = true,
  className,
  label,
  ...rest
}) {
  const [currentProgress, setCurrentProgress] = useState(0)

  // 尺寸配置
  const sizeConfig = {
    sm: { dimension: 60, stroke: 4 },
    md: { dimension: 100, stroke: 6 },
    lg: { dimension: 140, stroke: 8 },
    xl: { dimension: 180, stroke: 10 },
  }

  const config = sizeConfig[size] || sizeConfig.md
  const dimension = config.dimension
  const stroke = strokeWidth || config.stroke
  const radius = (dimension - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const safePercentage = Math.max(0, Math.min(100, percentage))

  // 动画效果
  useEffect(() => {
    if (animated) {
      const duration = 1500
      const startTime = Date.now()

      const animate = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)
        // 使用 easeOutCubic 缓动函数
        const easeProgress = 1 - Math.pow(1 - progress, 3)
        setCurrentProgress(easeProgress * safePercentage)

        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }

      requestAnimationFrame(animate)
    } else {
      setCurrentProgress(safePercentage)
    }
  }, [safePercentage, animated])

  const offset = circumference - (currentProgress / 100) * circumference

  const containerClasses = classNames(
    'progress-bar',
    `progress-bar--${color}`,
    `progress-bar--${size}`,
    className
  )

  return (
    <motion.div
      className={containerClasses}
      initial={animated ? { opacity: 0, scale: 0.8 } : false}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      {...rest}
    >
      <svg
        className="progress-bar__svg"
        width={dimension}
        height={dimension}
        viewBox={`0 0 ${dimension} ${dimension}`}
      >
        {/* 背景圆环 */}
        <circle
          className="progress-bar__background"
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          strokeWidth={stroke}
          fill="none"
        />

        {/* 进度圆环 */}
        <circle
          className="progress-bar__progress"
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${dimension / 2} ${dimension / 2})`}
        />

        {/* 发光滤镜 */}
        <defs>
          <filter id={`glow-${color}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      {/* 中心标签 */}
      {showLabel && (
        <div className="progress-bar__label">
          {label || (
            <>
              <span className="progress-bar__value">
                {Math.round(currentProgress)}
              </span>
              <span className="progress-bar__unit">%</span>
            </>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default ProgressBar
