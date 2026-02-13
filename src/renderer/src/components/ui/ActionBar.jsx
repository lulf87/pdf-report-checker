import React from 'react'
import { motion } from 'framer-motion'
import { Button, Space, Switch, Tooltip } from 'antd'
import {
  ReloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  UploadOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import classNames from 'classnames'
import './ActionBar.css'

/**
 * 底部操作栏组件
 * @param {Object} props
 * @param {Array} [props.actions] - 自定义操作按钮数组
 * @param {boolean} [props.llmEnabled] - LLM 是否启用
 * @param {Function} [props.onLlmToggle] - LLM 切换回调
 * @param {Function} [props.onCheck] - 重新核对回调
 * @param {Function} [props.onReset] - 重置/上传新文件回调
 * @param {Function} [props.onExportPdf] - 导出 PDF 回调
 * @param {Function} [props.onExportExcel] - 导出 Excel 回调
 * @param {boolean} [props.showExport] - 是否显示导出按钮
 * @param {boolean} [props.fixed] - 是否固定在底部
 * @param {string} [props.className] - 额外的类名
 */
function ActionBar({
  actions,
  llmEnabled = false,
  onLlmToggle,
  onCheck,
  onReset,
  onExportPdf,
  onExportExcel,
  showExport = true,
  fixed = true,
  className,
  ...rest
}) {
  const barClasses = classNames(
    'action-bar',
    {
      'action-bar--fixed': fixed,
    },
    className
  )

  // 默认操作按钮
  const defaultActions = (
    <>
      {/* LLM 开关 */}
      {onLlmToggle && (
        <div className="action-bar__llm-toggle">
          <Tooltip title="启用后，当OCR识别失败时会调用大模型(LLM)进行辅助识别，可提高识别准确率但会增加处理时间">
            <InfoCircleOutlined className="action-bar__llm-icon" />
          </Tooltip>
          <span className="action-bar__llm-label">
            <ThunderboltOutlined /> LLM 增强
          </span>
          <Switch
            checked={llmEnabled}
            onChange={onLlmToggle}
            checkedChildren="ON"
            unCheckedChildren="OFF"
            size="small"
          />
        </div>
      )}

      {/* 核对按钮 */}
      {onCheck && (
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={onCheck}
          className="action-bar__btn action-bar__btn--primary"
        >
          {showExport ? '重新核对' : '开始核对'}
        </Button>
      )}

      {/* 导出按钮 */}
      {showExport && (
        <>
          {onExportPdf && (
            <Button
              icon={<FilePdfOutlined />}
              onClick={onExportPdf}
              className="action-bar__btn"
            >
              导出 PDF
            </Button>
          )}
          {onExportExcel && (
            <Button
              icon={<FileExcelOutlined />}
              onClick={onExportExcel}
              className="action-bar__btn"
            >
              导出 Excel
            </Button>
          )}
        </>
      )}

      {/* 重置按钮 */}
      {onReset && (
        <Button
          icon={<UploadOutlined />}
          onClick={onReset}
          className="action-bar__btn"
        >
          {showExport ? '上传新文件' : '重新选择'}
        </Button>
      )}
    </>
  )

  return (
    <motion.div
      className={barClasses}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      {...rest}
    >
      {/* 装饰性顶部发光线 */}
      <div className="action-bar__glow-line" />

      {/* 内容区域 */}
      <div className="action-bar__content">
        <Space size="middle" wrap>
          {actions || defaultActions}
        </Space>
      </div>

      {/* 装饰性边角 */}
      <div className="action-bar__corner action-bar__corner--tl" />
      <div className="action-bar__corner action-bar__corner--tr" />
      <div className="action-bar__corner action-bar__corner--bl" />
      <div className="action-bar__corner action-bar__corner--br" />
    </motion.div>
  )
}

export default ActionBar
