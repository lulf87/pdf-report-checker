/**
 * FileCardAdapter - FileCard API适配器
 * 将旧版props转换为新版props，确保向后兼容
 *
 * 旧版API -> 新版API映射:
 * - fileInfo (Object) -> filename, fileType, fileSize (展开)
 *   - fileInfo.filename -> filename
 *   - fileInfo.file_type -> fileType
 * - checkTime (string) -> 新组件不再需要
 * - pageCount (number) -> 新组件不再需要
 * - onExport (Function) -> 新组件不再需要（使用onClick替代）
 *
 * 适配器行为:
 * - 将旧版的fileInfo对象展开为新版的独立props
 * - 移除checkTime和pageCount显示（新组件不支持）
 * - onExport转换为onClick（如果需要）
 */

import React, { useMemo } from 'react'
import NewFileCard from '../ui-new/Card/FileCard'

/**
 * FileCard适配器组件
 * @param {Object} props
 * @param {Object} props.fileInfo - 文件信息对象 (旧版)
 * @param {string} props.fileInfo.filename - 文件名
 * @param {string} props.fileInfo.file_type - 文件类型
 * @param {string} [props.checkTime] - 核对时间 (旧版，新组件不支持)
 * @param {number} [props.pageCount] - 页数 (旧版，新组件不支持)
 * @param {Function} [props.onExport] - 导出回调函数 (旧版，新组件不支持)
 * @param {Function} [props.onRemove] - 移除文件回调 (新版支持)
 * @param {Function} [props.onClick] - 点击卡片回调 (新版支持)
 * @param {string} [props.className] - 额外的类名
 */
function FileCardAdapter({
  fileInfo,
  checkTime, // 新组件不支持，忽略
  pageCount, // 新组件不支持，忽略
  onExport, // 新组件不支持，如果需要可以转换为onClick
  onRemove,
  onClick,
  className,
  ...restProps
}) {
  // 提取文件名和类型
  const { filename, fileType } = useMemo(() => {
    return {
      filename: fileInfo?.filename || '',
      fileType: fileInfo?.file_type || '',
    }
  }, [fileInfo])

  // 如果有onExport但没有onClick，将onExport作为onClick使用
  const handleClick = onClick || onExport

  return (
    <NewFileCard
      filename={filename}
      fileType={fileType}
      uploaded={true}
      onRemove={onRemove}
      onClick={handleClick}
      className={className}
      {...restProps}
    />
  )
}

export default FileCardAdapter
