/**
 * StatCardAdapter - StatCard API适配器
 * 将旧版props转换为新版props，确保向后兼容
 *
 * 旧版API -> 新版API映射:
 * - title (string) -> title (string) [保持不变]
 * - value (string|number) -> value (string|number) [保持不变]
 * - icon (ReactNode) -> icon (ReactNode) [保持不变]
 * - type (string) -> type (string) [保持不变]
 * - suffix (string) -> suffix (string) [保持不变]
 * - prefix (string) -> prefix (string) [保持不变]
 * - decimals (number) -> 新组件不再需要，value直接格式化
 * - animated (boolean) -> 新组件不再需要
 * - delay (number) -> 新组件不再需要
 * - className (string) -> className (string) [保持不变]
 *
 * 新增props:
 * - trend (number) - 趋势值
 * - trendLabel (string) - 趋势标签
 */

import React, { useMemo } from 'react'
import NewStatCard from '../ui-new/Card/StatCard'

/**
 * StatCard适配器组件
 * @param {Object} props
 * @param {string} props.title - 标题
 * @param {string|number} props.value - 数值
 * @param {React.ReactNode} [props.icon] - 图标
 * @param {'success'|'error'|'warning'|'info'|'blue'|'cyan'|'purple'} [props.type] - 类型/颜色
 * @param {string} [props.suffix] - 后缀
 * @param {string} [props.prefix] - 前缀
 * @param {number} [props.decimals] - 小数位数 (旧版，新组件不再使用)
 * @param {boolean} [props.animated] - 是否有入场动画 (旧版，新组件不再使用)
 * @param {number} [props.delay] - 动画延迟时间(ms) (旧版，新组件不再使用)
 * @param {number} [props.trend] - 趋势值(正数上升，负数下降)
 * @param {string} [props.trendLabel] - 趋势标签
 * @param {string} [props.className] - 额外的类名
 */
function StatCardAdapter({
  title,
  value,
  icon,
  type = 'blue',
  suffix = '',
  prefix = '',
  decimals = 0,
  animated = true,
  delay = 0,
  trend,
  trendLabel,
  className,
  ...restProps
}) {
  // 格式化数值（处理decimals）
  const formattedValue = useMemo(() => {
    if (typeof value === 'number' && decimals > 0) {
      return Number(value.toFixed(decimals))
    }
    return value
  }, [value, decimals])

  // 注意：animated和delay在新组件中不再使用
  // 如果需要动画效果，需要在父组件中自行实现

  return (
    <NewStatCard
      title={title}
      value={formattedValue}
      icon={icon}
      type={type}
      suffix={suffix}
      prefix={prefix}
      trend={trend}
      trendLabel={trendLabel}
      className={className}
      {...restProps}
    />
  )
}

export default StatCardAdapter
