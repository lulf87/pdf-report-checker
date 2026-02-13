import React from 'react'
import { CheckCircleOutlined, CloseCircleOutlined, AppstoreOutlined, PieChartOutlined } from '@ant-design/icons'
import StatCard from './StatCard'
import styles from './styles.module.css'

/**
 * 统计摘要面板组件
 * @param {Object} props
 * @param {Object} props.result - 核对结果对象
 * @param {number} props.result.total_components - 总部件数
 * @param {number} props.result.passed_components - 通过数
 * @param {number} props.result.failed_components - 失败数
 */
function DashboardStats({ result }) {
  if (!result) return null

  const {
    total_components = 0,
    passed_components = 0,
    failed_components = 0,
  } = result

  const passRate = total_components > 0
    ? ((passed_components / total_components) * 100).toFixed(1)
    : '0.0'

  const stats = [
    {
      title: '总部件数',
      value: total_components,
      icon: <AppstoreOutlined />,
      color: 'medical',
    },
    {
      title: '通过',
      value: passed_components,
      icon: <CheckCircleOutlined />,
      color: 'pass',
    },
    {
      title: '失败',
      value: failed_components,
      icon: <CloseCircleOutlined />,
      color: 'fail',
    },
    {
      title: '通过率',
      value: passRate,
      suffix: '%',
      icon: <PieChartOutlined />,
      color: 'medical',
    },
  ]

  return (
    <div className={styles.dashboardStats}>
      {stats.map((stat, index) => (
        <StatCard key={index} {...stat} />
      ))}
    </div>
  )
}

export default DashboardStats
