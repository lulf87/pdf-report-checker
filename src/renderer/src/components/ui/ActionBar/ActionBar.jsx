import React from 'react'
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
import styles from './ActionBar.module.css'

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
    styles.actionBar,
    {
      [styles['actionBar--fixed']]: fixed,
    },
    className
  )

  // 默认操作按钮
  const defaultActions = (
    <>
      {/* LLM 开关 */}
      {onLlmToggle && (
        <div className={styles.actionBar__llmToggle}>
          <Tooltip title="启用后，当OCR识别失败时会调用大模型(LLM)进行辅助识别，可提高识别准确率但会增加处理时间">
            <InfoCircleOutlined className={styles.actionBar__llmIcon} />
          </Tooltip>
          <span className={styles.actionBar__llmLabel}>
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
          className={`${styles.actionBar__btn} ${styles['actionBar__btn--primary']}`}
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
              className={styles.actionBar__btn}
            >
              导出 PDF
            </Button>
          )}
          {onExportExcel && (
            <Button
              icon={<FileExcelOutlined />}
              onClick={onExportExcel}
              className={styles.actionBar__btn}
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
          className={styles.actionBar__btn}
        >
          {showExport ? '上传新文件' : '重新选择'}
        </Button>
      )}
    </>
  )

  return (
    <div className={barClasses} {...rest}>
      {/* 装饰性顶部发光线 */}
      <div className={styles.actionBar__glowLine} />

      {/* 内容区域 */}
      <div className={styles.actionBar__content}>
        <Space size="middle" wrap>
          {actions || defaultActions}
        </Space>
      </div>

      {/* 装饰性边角 */}
      <div className={`${styles.actionBar__corner} ${styles['actionBar__corner--tl']}`} />
      <div className={`${styles.actionBar__corner} ${styles['actionBar__corner--tr']}`} />
      <div className={`${styles.actionBar__corner} ${styles['actionBar__corner--bl']}`} />
      <div className={`${styles.actionBar__corner} ${styles['actionBar__corner--br']}`} />
    </div>
  )
}

export default ActionBar
