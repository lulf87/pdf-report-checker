import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, CalendarOutlined } from '@ant-design/icons'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C03: 生产日期格式检查详情组件
 * @param {Object} props
 * @param {string} props.tableFormat - 表格中的日期格式
 * @param {string} props.labelFormat - 标签上的日期格式
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.errorMessage - 错误信息
 * @param {string} props.tableDate - 表格中的日期值
 * @param {string} props.labelDate - 标签上的日期值
 */
function C03DateFormatDetail({
  tableFormat = '',
  labelFormat = '',
  passed = true,
  errorMessage = '',
  tableDate = '',
  labelDate = '',
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 格式化显示
  const formatDisplay = (format) => {
    if (!format) return '-'
    return format
  }

  return (
    <div className="check-detail">
      <motion.div
        className="check-detail__header"
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
        whileTap={{ scale: 0.99 }}
      >
        <div className="check-detail__header-left">
          <motion.span
            className="check-detail__expand-icon"
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <DownOutlined />
          </motion.span>
          <span className="check-detail__title">日期格式检查详情</span>
        </div>
        <div className="check-detail__header-right">
          <StatusBadge
            status={passed ? 'success' : 'error'}
            text={passed ? '格式一致' : '格式不一致'}
            size="sm"
          />
        </div>
      </motion.div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="check-detail__content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <div className="check-detail__format-comparison">
              {/* 表格日期格式 */}
              <div className="check-detail__format-card">
                <div className="check-detail__format-label">
                  <CalendarOutlined className="check-detail__format-icon" />
                  <span>表格中的生产日期</span>
                </div>
                <div className="check-detail__format-value">
                  {tableDate || '-'}
                </div>
                <div className="check-detail__format-pattern">
                  格式: {formatDisplay(tableFormat)}
                </div>
              </div>

              {/* 对比箭头 */}
              <div className="check-detail__format-compare">
                <motion.div
                  className={`check-detail__compare-indicator ${passed ? 'match' : 'mismatch'}`}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  {passed ? (
                    <CheckCircleOutlined className="check-detail__compare-icon success" />
                  ) : (
                    <CloseCircleOutlined className="check-detail__compare-icon error" />
                  )}
                </motion.div>
              </div>

              {/* 标签日期格式 */}
              <div className="check-detail__format-card">
                <div className="check-detail__format-label">
                  <CalendarOutlined className="check-detail__format-icon" />
                  <span>标签上的生产日期</span>
                </div>
                <div className="check-detail__format-value">
                  {labelDate || '-'}
                </div>
                <div className="check-detail__format-pattern">
                  格式: {formatDisplay(labelFormat)}
                </div>
              </div>
            </div>

            {!passed && errorMessage && (
              <div className="check-detail__error">
                <CloseCircleOutlined className="check-detail__error-icon" />
                <span className="check-detail__error-text">{errorMessage}</span>
              </div>
            )}

            {/* 格式说明 */}
            <div className="check-detail__format-note">
              <span className="check-detail__note-label">说明:</span>
              <span className="check-detail__note-text">
                以标签格式为准，表格格式应与标签格式保持一致
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C03DateFormatDetail
