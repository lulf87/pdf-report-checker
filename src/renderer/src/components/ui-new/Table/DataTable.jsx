import React, { useState, useMemo } from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import styles from './DataTable.module.css'

/**
 * DataTable - 数据表格组件
 * @param {Object} props
 * @param {Array} props.columns - 列配置
 * @param {Array} props.data - 数据数组
 * @param {boolean} [props.sortable] - 是否可排序
 * @param {boolean} [props.selectable] - 是否可选择行
 * @param {Array} [props.selectedKeys] - 选中行的key数组
 * @param {Function} [props.onSelectionChange] - 选择变化回调
 * @param {Function} [props.onRowClick] - 行点击回调
 * @param {string} [props.rowKey] - 行唯一标识字段
 * @param {string} [props.className] - 额外的类名
 * @param {boolean} [props.loading] - 加载状态
 * @param {React.ReactNode} [props.emptyText] - 空数据提示
 */
function DataTable({
  columns,
  data,
  sortable = false,
  selectable = false,
  selectedKeys = [],
  onSelectionChange,
  onRowClick,
  rowKey = 'id',
  className,
  loading = false,
  emptyText = '暂无数据',
  ...rest
}) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10

  // 排序处理
  const sortedData = useMemo(() => {
    if (!sortable || !sortConfig.key) return data

    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key]
      const bValue = b[sortConfig.key]

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })
  }, [data, sortConfig, sortable])

  // 分页处理
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, currentPage])

  const totalPages = Math.ceil(data.length / pageSize)

  const handleSort = (key) => {
    if (!sortable) return

    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      onSelectionChange?.(data.map((item) => item[rowKey]))
    } else {
      onSelectionChange?.([])
    }
  }

  const handleSelectRow = (key, e) => {
    e.stopPropagation()
    const newSelection = selectedKeys.includes(key)
      ? selectedKeys.filter((k) => k !== key)
      : [...selectedKeys, key]
    onSelectionChange?.(newSelection)
  }

  const isAllSelected = data.length > 0 && selectedKeys.length === data.length
  const isIndeterminate = selectedKeys.length > 0 && selectedKeys.length < data.length

  const getRowStatus = (record) => {
    if (record.status === 'error') return styles['dataTable__row--error']
    if (record.status === 'warning') return styles['dataTable__row--warning']
    if (record.status === 'success') return styles['dataTable__row--success']
    return ''
  }

  return (
    <div className={classNames(styles.dataTable, className)} {...rest}>
      <div className={styles.dataTable__container}>
        <table className={styles.dataTable__table}>
          <thead className={styles.dataTable__thead}>
            <tr>
              {selectable && (
                <th className={classNames(styles.dataTable__th, styles.dataTable__th--checkbox)}>
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={(el) => el && (el.indeterminate = isIndeterminate)}
                    onChange={handleSelectAll}
                    className={styles.dataTable__checkbox}
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={classNames(styles.dataTable__th, {
                    [styles['dataTable__th--sortable']]: sortable && col.sortable !== false,
                    [styles['dataTable__th--sorted']]: sortConfig.key === col.key,
                  })}
                  style={{ width: col.width }}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  <div className={styles.dataTable__thContent}>
                    <span>{col.title}</span>
                    {sortable && col.sortable !== false && (
                      <span className={styles.dataTable__sortIcon}>
                        {sortConfig.key === col.key ? (
                          sortConfig.direction === 'asc' ? (
                            <ChevronUp size={14} />
                          ) : (
                            <ChevronDown size={14} />
                          )
                        ) : (
                          <ChevronUp size={14} className={styles.dataTable__sortIcon--inactive} />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={styles.dataTable__tbody}>
            {loading ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className={styles.dataTable__loading}>
                  <div className={styles.dataTable__spinner} />
                  <span>加载中...</span>
                </td>
              </tr>
            ) : paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className={styles.dataTable__empty}>
                  {emptyText}
                </td>
              </tr>
            ) : (
              paginatedData.map((record, index) => (
                <tr
                  key={record[rowKey] || index}
                  className={classNames(styles.dataTable__row, getRowStatus(record), {
                    [styles['dataTable__row--clickable']]: onRowClick,
                    [styles['dataTable__row--selected']]: selectedKeys.includes(record[rowKey]),
                  })}
                  onClick={() => onRowClick?.(record)}
                >
                  {selectable && (
                    <td
                      className={classNames(styles.dataTable__td, styles.dataTable__td--checkbox)}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={selectedKeys.includes(record[rowKey])}
                        onChange={(e) => handleSelectRow(record[rowKey], e)}
                        className={styles.dataTable__checkbox}
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td key={col.key} className={styles.dataTable__td}>
                      {col.render ? col.render(record[col.key], record, index) : record[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className={styles.dataTable__pagination}>
          <button
            className={styles.dataTable__pageBtn}
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <span className={styles.dataTable__pageInfo}>
            {currentPage} / {totalPages}
          </span>
          <button
            className={styles.dataTable__pageBtn}
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => p + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  )
}

DataTable.propTypes = {
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      title: PropTypes.node.isRequired,
      width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      sortable: PropTypes.bool,
      render: PropTypes.func,
    })
  ).isRequired,
  data: PropTypes.array.isRequired,
  sortable: PropTypes.bool,
  selectable: PropTypes.bool,
  selectedKeys: PropTypes.array,
  onSelectionChange: PropTypes.func,
  onRowClick: PropTypes.func,
  rowKey: PropTypes.string,
  className: PropTypes.string,
  loading: PropTypes.bool,
  emptyText: PropTypes.node,
}

export default DataTable
