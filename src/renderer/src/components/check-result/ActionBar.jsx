import React from 'react'
import { Button, Space, Switch, Tooltip, message } from 'antd'
import {
  ReloadOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  UploadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

/**
 * 底部操作栏组件
 * @param {Object} props
 * @param {Function} props.onCheck - 重新核对回调
 * @param {Function} props.onReset - 重置回调
 * @param {Function} [props.onExport] - 导出回调
 * @param {boolean} [props.llmEnabled] - LLM 是否启用
 * @param {Function} [props.onLlmToggle] - LLM 切换回调
 * @param {boolean} [props.showExport] - 是否显示导出按钮
 */
function ActionBar({
  onCheck,
  onReset,
  onExport,
  llmEnabled = false,
  onLlmToggle,
  showExport = true,
}) {
  const handleExport = async (format) => {
    if (!onExport) return
    try {
      await onExport(format)
      message.success(`报告已导出`)
    } catch (error) {
      message.error(`导出失败: ${error.message}`)
    }
  }

  return (
    <div className={styles.actionBar}>
      <Space size="middle" wrap>
        {/* LLM 开关 */}
        {onLlmToggle && (
          <div className={styles.llmToggle}>
            <Tooltip title="启用后，当OCR识别失败时会调用大模型(LLM)进行辅助识别，可提高识别准确率但会增加处理时间">
              <InfoCircleOutlined className={styles.llmToggleIcon} />
            </Tooltip>
            <span>LLM 增强识别:</span>
            <Switch
              checked={llmEnabled}
              onChange={onLlmToggle}
              checkedChildren="开启"
              unCheckedChildren="关闭"
            />
          </div>
        )}

        <Button icon={<ReloadOutlined />} onClick={onCheck}>
          {showExport ? '重新核对' : '开始核对'}
        </Button>

        {showExport && onExport && (
          <>
            <Button
              icon={<FilePdfOutlined />}
              onClick={() => handleExport('pdf')}
            >
              导出 PDF
            </Button>
            <Button
              icon={<FileExcelOutlined />}
              onClick={() => handleExport('excel')}
            >
              导出 Excel
            </Button>
          </>
        )}

        <Button icon={<UploadOutlined />} onClick={onReset}>
          {showExport ? '上传新文件' : '重新选择'}
        </Button>
      </Space>
    </div>
  )
}

export default ActionBar
