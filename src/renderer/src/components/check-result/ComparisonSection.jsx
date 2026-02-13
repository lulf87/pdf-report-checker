import React from 'react'
import { Card, Table, Tag, Typography } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 首页与第三页比对组件
 * @param {Object} props
 * @param {Array} props.data - 比对数据数组
 */
function ComparisonSection({ data = [] }) {
  if (!data || data.length === 0) {
    return null
  }

  const mismatchCount = data.filter((item) => !item.is_match).length
  const allMatch = mismatchCount === 0

  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
    },
    {
      title: '首页值',
      dataIndex: 'table_value',
      key: 'table_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '第三页值',
      dataIndex: 'ocr_value',
      key: 'ocr_value',
      render: (text) => text || <Text type="secondary">/</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_match',
      key: 'is_match',
      width: 100,
      render: (isMatch) =>
        isMatch ? (
          <Tag color="success" icon={<CheckCircleOutlined />} className={styles.statusTag}>
            一致
          </Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />} className={styles.statusTag}>
            不一致
          </Tag>
        ),
    },
  ]

  return (
    <Card
      title="首页与第三页比对"
      className={styles.comparisonSection}
      extra={
        <Tag color={allMatch ? 'success' : 'error'}>
          {allMatch ? '全部一致' : `${mismatchCount} 处不一致`}
        </Tag>
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="field_name"
        pagination={false}
        size="middle"
        rowClassName={(record) =>
          !record.is_match ? styles.rowMismatch : ''
        }
      />
    </Card>
  )
}

export default ComparisonSection
