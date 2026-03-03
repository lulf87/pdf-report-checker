/**
 * CheckItemCardAdapter - CheckItemCard API适配器
 * 将旧版props转换为新版props，确保向后兼容
 *
 * 旧版API -> 新版API映射:
 * - code (string) -> 在title中显示为前缀或忽略
 * - name (string) -> title (string)
 * - status (旧: 'pass'|'fail'|'warning'|'skip') -> status (新: 'success'|'error'|'warning'|'pending')
 *   - 'pass' -> 'success'
 *   - 'fail' -> 'error'
 *   - 'warning' -> 'warning'
 *   - 'skip' -> 'pending'
 * - errorCount (number) -> 新组件不再需要，转换为description的一部分
 * - warningCount (number) -> 新组件不再需要，转换为description的一部分
 * - defaultExpanded (boolean) -> expanded (boolean)
 * - description (string) -> description (string)
 * - children (ReactNode) -> children (ReactNode)
 */

import React, { useMemo } from 'react'
import NewCheckItemCard from '../ui-new/Card/CheckItemCard'

/**
 * 状态映射：旧版状态 -> 新版状态
 */
const STATUS_MAP = {
  pass: 'success',
  fail: 'error',
  warning: 'warning',
  skip: 'pending'
}

/**
 * CheckItemCard适配器组件
 * @param {Object} props
 * @param {string} [props.code] - 核对项编号 (旧版)
 * @param {string} props.name - 核对项名称 (旧版) -> 映射为title
 * @param {string} [props.status] - 状态: pass/fail/warning/skip (旧版)
 * @param {string} [props.description] - 描述文本
 * @param {number} [props.errorCount] - 错误计数 (旧版)
 * @param {number} [props.warningCount] - 警告计数 (旧版)
 * @param {boolean} [props.defaultExpanded] - 是否默认展开 (旧版) -> 映射为expanded
 * @param {React.ReactNode} [props.children] - 详情区域内容
 * @param {Function} [props.onClick] - 点击事件回调
 * @param {string} [props.className] - 额外的类名
 */
function CheckItemCardAdapter({
  code,
  name,
  status = 'pass',
  description,
  errorCount = 0,
  warningCount = 0,
  defaultExpanded = false,
  children,
  onClick,
  className,
  ...restProps
}) {
  // 转换title：如果有code，则显示为前缀
  const title = useMemo(() => {
    if (code && name) {
      return `${code} ${name}`
    }
    return name || code || ''
  }, [code, name])

  // 转换状态
  const mappedStatus = useMemo(() => {
    return STATUS_MAP[status] || 'pending'
  }, [status])

  // 转换展开状态
  const expanded = defaultExpanded

  // 构建增强的描述文本（包含错误/警告计数信息）
  const enhancedDescription = useMemo(() => {
    const parts = []
    if (description) {
      parts.push(description)
    }

    const issueParts = []
    if (errorCount > 0) {
      issueParts.push(`${errorCount} 个错误`)
    }
    if (warningCount > 0) {
      issueParts.push(`${warningCount} 个警告`)
    }

    if (issueParts.length > 0) {
      if (parts.length > 0) {
        parts.push(`(${issueParts.join('，')})`)
      } else {
        parts.push(issueParts.join('，'))
      }
    }

    return parts.join(' ') || undefined
  }, [description, errorCount, warningCount])

  // 判断是否可展开（有子内容）
  const expandable = Boolean(children)

  return (
    <NewCheckItemCard
      title={title}
      description={enhancedDescription}
      status={mappedStatus}
      expandable={expandable}
      expanded={expanded}
      onClick={onClick}
      className={className}
      {...restProps}
    >
      {children}
    </NewCheckItemCard>
  )
}

export default CheckItemCardAdapter
