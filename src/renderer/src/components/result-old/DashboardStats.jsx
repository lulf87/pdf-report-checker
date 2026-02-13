import React from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  AppstoreOutlined,
  PieChartOutlined,
} from '@ant-design/icons'
import { StatCard, ProgressBar } from '../ui'
import './DashboardStats.module.css'

/**
 * 统计仪表盘组件 - 科技感风格
 * @param {Object} props
 * @param {Object} props.result - 核对结果对象
 * @param {number} props.result.total_components - 总字段数
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
    : 0

  // 统计数据
  const stats = [
    {
      title: '总字段',
      value: total_components,
      icon: <AppstoreOutlined />,
      type: 'blue',
    },
    {
      title: '通过',
      value: passed_components,
      icon: <CheckCircleOutlined />,
      type: 'success',
    },
    {
      title: '失败',
      value: failed_components,
      icon: <CloseCircleOutlined />,
      type: 'error',
    },
    {
      title: '通过率',
      value: passRate,
      suffix: '%',
      icon: <PieChartOutlined />,
      type: parseFloat(passRate) >= 80 ? 'success' : parseFloat(passRate) >= 60 ? 'warning' : 'error',
    },
  ]

  // 动画配置
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.34, 1.56, 0.64, 1],
      },
    },
  }

  return (
    <motion.div
      className="dashboard-stats"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* 左侧：统计卡片网格 */}
      <div className="dashboard-stats__cards">
        {stats.map((stat, index) => (
          <motion.div key={index} variants={itemVariants}>
            <StatCard
              title={stat.title}
              value={stat.value}
              suffix={stat.suffix}
              icon={stat.icon}
              type={stat.type}
              delay={index * 100}
            />
          </motion.div>
        ))}
      </div>

      {/* 右侧：环形进度图 */}
      <motion.div
        className="dashboard-stats__progress"
        variants={itemVariants}
      >
        <div className="dashboard-stats__progress-wrapper">
          <ProgressBar
            percentage={parseFloat(passRate)}
            size="xl"
            color={parseFloat(passRate) >= 80 ? 'success' : parseFloat(passRate) >= 60 ? 'warning' : 'error'}
          />
          <div className="dashboard-stats__progress-label">
            <span className="dashboard-stats__progress-title">总体通过率</span>
            <span className="dashboard-stats__progress-desc">
              {parseFloat(passRate) >= 90
                ? '优秀'
                : parseFloat(passRate) >= 80
                  ? '良好'
                  : parseFloat(passRate) >= 60
                    ? '一般'
                    : '需要关注'}
            </span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

export default DashboardStats
