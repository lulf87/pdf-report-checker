import React from 'react'
import { Card, Table, Typography, Alert } from 'antd'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 样品描述表格组件
 * @param {Object} props
 * @param {Object} props.data - 表格数据
 * @param {Array} props.data.headers - 表头数组
 * @param {Array} props.data.rows - 行数据数组
 */
function SampleTableSection({ data }) {
  if (!data) {
    return (
      <Card title="样品描述表格" className={styles.sampleTableSection}>
        <Alert message="未找到样品描述表格" type="warning" showIcon />
      </Card>
    )
  }

  const { headers = [], rows = [] } = data

  const columns = headers.map((header, index) => ({
    title: header,
    dataIndex: `col_${index}`,
    key: index,
    render: (text) => text || <Text type="secondary">/</Text>,
  }))

  const dataSource = rows.map((row, rowIndex) => {
    const rowData = { key: rowIndex }
    row.forEach((cell, cellIndex) => {
      rowData[`col_${cellIndex}`] = cell
    })
    return rowData
  })

  return (
    <Card title="样品描述表格" className={styles.sampleTableSection}>
      <Table
        columns={columns}
        dataSource={dataSource}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        size="middle"
        scroll={{ x: 'max-content' }}
      />
    </Card>
  )
}

export default SampleTableSection
