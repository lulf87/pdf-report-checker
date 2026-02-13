import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined } from '@ant-design/icons'
import DataTable from '../../ui/DataTable'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C04: 样品描述表格各部件字段比对详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件检查数据
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 部件总数
 * @param {number} props.passedComponents - 通过部件数
 */
function C04SampleTableDetail({
  components = [],
  passed = true,
  totalComponents = 0,
  passedComponents = 0,
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedRowKeys, setExpandedRowKeys] = useState([])

  // 默认展示数据
  const defaultData = [
    {
      key: '1',
      componentName: '主机',
      fieldName: '规格型号',
      tableValue: 'ABC-123',
      labelValue: 'ABC-123',
      status: 'match',
      isUnused: false,
    },
    {
      key: '2',
      componentName: '主机',
      fieldName: '序列号批号',
      tableValue: 'SN001',
      labelValue: 'SN001',
      status: 'match',
      isUnused: false,
    },
    {
      key: '3',
      componentName: '推车',
      fieldName: '规格型号',
      tableValue: '/',
      labelValue: '',
      status: 'match',
      isUnused: true,
    },
  ]

  const dataSource = components.length > 0 ? components : defaultData

  // 展开行的列定义
  const expandedColumns = [
    {
      title: '字段',
      dataIndex: 'fieldName',
      key: 'fieldName',
      width: '25%',
      render: (text) => <span className="check-detail__sub-field">{text}</span>,
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
      render: (status, record) => (
        <StatusBadge
          status={status === 'match' ? 'success' : record.isUnused ? 'warning' : 'error'}
          text={status === 'match' ? '一致' : record.isUnused ? '未使用' : '不一致'}
          icon={status === 'match' ? <CheckCircleOutlined /> : record.isUnused ? <WarningOutlined /> : <CloseCircleOutlined />}
          size="sm"
        />
      ),
    },
  ]

  // 主表格列定义
  const columns = [
    {
      title: '部件名称',
      dataIndex: 'componentName',
      key: 'componentName',
      width: '30%',
      render: (text, record) => (
        <div className="check-detail__component-cell">
          <span className="check-detail__component-name">{text}</span>
          {record.isUnused && (
            <StatusBadge status="warning" text="本次检测未使用" size="sm" />
          )}
        </div>
      ),
    },
    {
      title: '字段数',
      dataIndex: 'fieldCount',
      key: 'fieldCount',
      width: '20%',
      align: 'center',
      render: (text, record) => (
        <span className="check-detail__field-count">
          {record.fields?.length || 0} 个字段
        </span>
      ),
    },
    {
      title: '通过/失败',
      dataIndex: 'passFail',
      key: 'passFail',
      width: '25%',
      align: 'center',
      render: (text, record) => {
        const fields = record.fields || []
        const passCount = fields.filter(f => f.status === 'match').length
        const failCount = fields.length - passCount
        return (
          <div className="check-detail__pass-fail">
            <span className="check-detail__pass-count">{passCount} 通过</span>
            {failCount > 0 && (
              <>
                <span className="check-detail__separator"> / </span>
                <span className="check-detail__fail-count">{failCount} 失败</span>
              </>
            )}
          </div>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '25%',
      align: 'center',
      render: (status, record) => {
        const fields = record.fields || []
        const allMatch = fields.every(f => f.status === 'match')
        return (
          <StatusBadge
            status={allMatch ? 'success' : record.isUnused ? 'warning' : 'error'}
            text={allMatch ? '通过' : record.isUnused ? '未使用' : '失败'}
            icon={allMatch ? <CheckCircleOutlined /> : record.isUnused ? <WarningOutlined /> : <CloseCircleOutlined />}
            size="sm"
          />
        )
      },
    },
  ]

  // 处理数据，按部件分组
  const groupedData = dataSource.reduce((acc, item) => {
    const existing = acc.find(i => i.componentName === item.componentName)
    if (existing) {
      existing.fields.push(item)
    } else {
      acc.push({
        key: item.componentName,
        componentName: item.componentName,
        isUnused: item.isUnused,
        fields: [item],
      })
    }
    return acc
  }, [])

  // 展开行渲染
  const expandedRowRender = (record) => {
    return (
      <div className="check-detail__expanded-content">
        <DataTable
          columns={expandedColumns}
          dataSource={record.fields.map((f, idx) => ({ ...f, key: `${record.key}-${idx}` }))}
          size="small"
          bordered={false}
          pagination={false}
          showHeader={true}
        />
      </div>
    )
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
          <span className="check-detail__title">样品描述表格详情</span>
        </div>
        <div className="check-detail__header-right">
          <span className="check-detail__summary">
            {passedComponents}/{totalComponents || groupedData.length} 部件通过
          </span>
          <StatusBadge
            status={passed ? 'success' : 'error'}
            text={passed ? '全部通过' : '存在失败'}
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
            <DataTable
              columns={columns}
              dataSource={groupedData}
              size="small"
              bordered={false}
              pagination={false}
              expandable={{
                expandedRowRender,
                expandedRowKeys,
                onExpandedRowsChange: setExpandedRowKeys,
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C04SampleTableDetail
