/**
 * UploadZoneAdapter - UploadZone API适配器
 * 将旧版props转换为新版props，确保向后兼容
 *
 * 旧版API -> 新版API映射:
 * - onUpload (Function) -> onUpload (Function) [行为变更]
 *   - 旧版: 接收上传成功后的文件信息对象 { file_id, filename, file_type }
 *   - 新版: 接收文件数组 files => void
 * - apiBaseUrl (string) -> 新组件不再需要，上传逻辑由父组件处理
 *
 * 适配器行为:
 * - 使用新版UploadZone组件
 * - 将新版的onUpload回调转换为旧版格式
 * - 父组件需要自行处理实际上传逻辑
 */

import React, { useState, useCallback } from 'react'
import NewUploadZone from '../ui-new/Upload/UploadZone'

/**
 * UploadZone适配器组件
 * @param {Object} props
 * @param {Function} props.onUpload - 上传成功回调 (旧版格式: ({ file_id, filename, file_type }) => void)
 * @param {string} [props.apiBaseUrl] - API基础URL (旧版，适配器中处理上传逻辑)
 */
function UploadZoneAdapter({ onUpload, apiBaseUrl, ...restProps }) {
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  // 处理文件上传
  const handleUpload = useCallback(async (files) => {
    if (!files || files.length === 0) return

    const file = files[0]
    setLoading(true)
    setProgress(0)

    // 模拟进度
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval)
          return 90
        }
        return prev + 10
      })
    }, 100)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      })

      clearInterval(progressInterval)
      setProgress(100)

      if (!response.ok) {
        throw new Error('上传失败')
      }

      const result = await response.json()

      if (result.success) {
        // 调用旧版回调格式
        onUpload?.({
          file_id: result.file_id,
          filename: result.filename,
          file_type: result.file_type,
        })
      } else {
        throw new Error(result.message || '上传失败')
      }
    } catch (error) {
      console.error('上传失败:', error)
      // 这里可以添加错误处理，比如显示toast通知
    } finally {
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, 500)
    }
  }, [apiBaseUrl, onUpload])

  return (
    <NewUploadZone
      onUpload={handleUpload}
      loading={loading}
      progress={progress}
      accept={['.pdf', '.docx']}
      maxSize={50}
      multiple={false}
      title="点击或拖拽文件到此处上传"
      hint="支持 PDF / DOCX 格式，文件大小不超过 50MB"
      {...restProps}
    />
  )
}

export default UploadZoneAdapter
