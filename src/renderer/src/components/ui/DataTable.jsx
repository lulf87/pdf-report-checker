import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table, ConfigProvider } from 'antd'
import { DownOutlined, RightOutlined } from '@ant-design/icons'
import classNames from 'classnames'
import './DataTable.css'

/**
 * 科技感数据表格组件
 * @param {Object} props
 * @param {Array} props.columns - 列定义
 * @param {Array} props.dataSource - 数据源
 * @param {Object} [props.expandable] - 展开配置
 * @param {boolean} [props.loading] - 加载状态
 * @param {string} [props.size] - 表格尺寸 'small' | 'middle' | 'large'
 * @param {boolean} [props.bordered] - 是否显示边框
 * @param {boolean} [props.showHeader] - 是否显示表头
 * @param {string} [props.className] - 额外的类名
 * @param {Function} [props.onRow] - 行事件处理
 * @param {Object} [props.pagination] - 分页配置
 */
function DataTable({
  columns = [],
  dataSource = [],
  expandable,
  loading = false,
  size = 'middle',
  bordered = false,
  showHeader = true,
  className,
  onRow,
  pagination = false,
  ...rest
}) {
  const [expandedRowKeys, setExpandedRowKeys] = useState([])

  // 自定义展开图标
  const expandIcon = ({ expanded, onExpand, record }) => (
    <motion.span
      className="data-table__expand-icon"
      onClick={(e) => onExpand(record, e)}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
    >
      {expanded ? <DownOutlined /> : <RightOutlined />}
    </motion.span>
  )

  // 合并展开配置
  const mergedExpandable = expandable
    ? {
        expandIcon,
        expandedRowKeys,
        onExpandedRowsChange: (keys) => setExpandedRowKeys(keys),
        expandRowByClick: true,
        ...expandable,
      }
    : undefined

  // 自定义行属性
  const customOnRow = (record, index) => {
    const baseProps = onRow ? onRow(record, index) : {}
    return {
      ...baseProps,
      className: classNames('data-table__row', baseProps.className),
    }
  }

  // Ant Design 主题配置
  const themeConfig = {
    token: {
      colorBgContainer: 'transparent',
      colorBorder: 'rgba(59, 130, 246, 0.2)',
      colorText: 'var(--text-primary)',
      colorTextSecondary: 'var(--text-secondary)',
    },
    components: {
      Table: {
        headerBg: 'rgba(59, 130, 246, 0.1)',
        headerColor: 'var(--text-primary)',
        rowHoverBg: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 0.2)',
        headerSplitColor: 'rgba(59, 130, 246, 0.2)',
      },
    },
  }

  const tableClasses = classNames('data-table', className)

  return (
    <ConfigProvider theme={themeConfig}>
      <motion.div
        className={tableClasses}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <Table
          columns={columns}
          dataSource={dataSource}
          expandable={mergedExpandable}
          loading={loading}
          size={size}
          bordered={bordered}
          showHeader={showHeader}
          onRow={customOnRow}
          pagination={pagination}
          rowKey={(record) => record.key || record.id}
          {...rest}
        />

        {/* 装饰性边角 */}
        <div className="data-table__corner data-table__corner--tl" />
        <div className="data-table__corner data-table__corner--tr" />
        <div className="data-table__corner data-table__corner--bl" />
        <div className="data-table__corner data-table__corner--br" />
      </motion.div>
    </ConfigProvider>
  )
}

export default DataTable
