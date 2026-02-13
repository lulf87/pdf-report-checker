import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import DataTable from '../../ui/DataTable'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C01: 首页与第三页一致性比对详情组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.errorMessage - 错误信息
 */
function C01HomeThirdDetail({ comparisons = [], passed = true, errorMessage = '' }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 默认展示数据（当没有传入数据时使用）
  const defaultData = [
    { key: '1', fieldName: '委 托 方', homeValue: '示例委托方', thirdPageValue: '示例委托方', status: 'match' },
    { key: '2', fieldName: '样品名称', homeValue: '心脏脉冲电场消融仪', thirdPageValue: '心脏脉冲电场消融仪', status: 'match' },
    { key: '3', fieldName: '型号规格', homeValue: 'ABC-123', thirdPageValue: 'ABC-123', status: 'match' },
  ]

  const dataSource = comparisons.length > 0 ? comparisons : defaultData

  const columns = [
    {
      title: '字段名',
      dataIndex: 'fieldName',
      key: 'fieldName',
      width: '25%',
      render: (text) => <span className="check-detail__field-name">{text}</span>,
    },
    {
      title: '首页值',
      dataIndex: 'homeValue',
      key: 'homeValue',
      width: '25%',
      render: (text) => <span className="check-detail__value">{text || '-'}</span>,
    },
    {
      title: '第三页值',
      dataIndex: 'thirdPageValue',
      key: 'thirdPageValue',
      width: '25%',
      render: (text) => <span className="check-detail__value">{text || '-'}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '25%',
      align: 'center',
      render: (status) => (
        <StatusBadge
          status={status === 'match' ? 'success' : 'error'}
          text={status === 'match' ? '一致' : '不一致'}
          icon={status === 'match' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          size="sm"
        />
      ),
    },
  ]

  return (
    <div className="check-detail">
      {/* 折叠头部 */}
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
          <span className="check-detail__title">字段比对详情</span>
        </div>
        <div className="check-detail__header-right">
          <StatusBadge
            status={passed ? 'success' : 'error'}
            text={passed ? '全部一致' : '存在不一致'}
            size="sm"
          />
        </div>
      </motion.div>

      {/* 展开内容 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="check-detail__content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <DataTable
              columns={columns}
              dataSource={dataSource}
              size="small"
              bordered={false}
              pagination={false}
            />
            {!passed && errorMessage && (
              <div className="check-detail__error">
                <CloseCircleOutlined className="check-detail__error-icon" />
                <span className="check-detail__error-text">{errorMessage}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C01HomeThirdDetail
