import React from 'react'
import classNames from 'classnames'
import { Table, Tag, Typography } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 字段比对表格组件
 * @param {Object} props
 * @param {Array} props.comparisons - 字段比对数据数组
 */
function FieldComparisonTable({ comparisons = [] }) {
  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 100,
    },
    {
      title: '表格值',
      dataIndex: 'table_value',
      key: 'table_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: 'OCR识别值',
      dataIndex: 'ocr_value',
      key: 'ocr_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_match',
      key: 'is_match',
      width: 80,
      render: (isMatch) =>
        isMatch ? (
          <Tag
            color="success"
            icon={<CheckCircleOutlined />}
            className={styles.statusTag}
          >
            一致
          </Tag>
        ) : (
          <Tag
            color="error"
            icon={<CloseCircleOutlined />}
            className={styles.statusTag}
          >
            不一致
          </Tag>
        ),
    },
  ]

  return (
    <Table
      size="small"
      pagination={false}
      dataSource={comparisons}
      rowKey="field_name"
      columns={columns}
      rowClassName={(record) =>
        !record.is_match ? styles.rowMismatch : ''
      }
      className={styles.fieldTable}
    />
  )
}

export default FieldComparisonTable
