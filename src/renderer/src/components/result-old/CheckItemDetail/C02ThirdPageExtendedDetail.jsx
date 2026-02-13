import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import DataTable from '../../ui/DataTable'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C02: 第三页扩展字段比对详情组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据
 * @param {boolean} props.passed - 是否通过
 * @param {string} props.checkType - 检查类型: 'all_sample_desc' | 'field_compare' | 'inconsistent'
 * @param {string} props.errorMessage - 错误信息
 */
function C02ThirdPageExtendedDetail({
  comparisons = [],
  passed = true,
  checkType = 'field_compare',
  errorMessage = '',
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 默认展示数据
  const defaultData = [
    {
      key: '1',
      fieldName: '型号规格',
      tableValue: 'ABC-123',
      labelValue: 'ABC-123',
      status: 'match',
    },
    {
      key: '2',
      fieldName: '生产日期',
      tableValue: '2026-01-08',
      labelValue: '2026-01-08',
      status: 'match',
    },
    {
      key: '3',
      fieldName: '产品编号/批号',
      tableValue: 'LOT001',
      labelValue: 'LOT001',
      status: 'match',
    },
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
      title: '表格值',
      dataIndex: 'tableValue',
      key: 'tableValue',
      width: '25%',
      render: (text) => <span className="check-detail__value">{text || '-'}</span>,
    },
    {
      title: '标签值',
      dataIndex: 'labelValue',
      key: 'labelValue',
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

  // 获取检查类型描述
  const getCheckTypeInfo = () => {
    switch (checkType) {
      case 'all_sample_desc':
        return { text: '全部见样品描述栏', status: 'info' }
      case 'field_compare':
        return { text: '字段比对', status: passed ? 'success' : 'error' }
      case 'inconsistent':
        return { text: '不一致', status: 'error' }
      default:
        return { text: '字段比对', status: passed ? 'success' : 'error' }
    }
  }

  const checkTypeInfo = getCheckTypeInfo()

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
          <span className="check-detail__title">扩展字段比对详情</span>
        </div>
        <div className="check-detail__header-right">
          <StatusBadge
            status={checkTypeInfo.status}
            text={checkTypeInfo.text}
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
            {checkType === 'all_sample_desc' ? (
              <div className="check-detail__info-box">
                <InfoCircleOutlined className="check-detail__info-icon" />
                <span className="check-detail__info-text">
                  三个字段值全部为"见"样品描述"栏"，判定为通过
                </span>
              </div>
            ) : (
              <>
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
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C02ThirdPageExtendedDetail
