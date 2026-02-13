/**
 * CheckListPanel - 核对内容清单总面板
 * 显示所有11个核对项（C01-C11）的汇总
 * 包含筛选功能：全部/仅错误/仅警告标签页
 * 按4个分组展示
 * 科技感数据大屏设计系统
 */

import React, { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Radio, Badge, Empty } from 'antd'
import {
  FileTextOutlined,
  PictureOutlined,
  ExperimentOutlined,
  NumberOutlined,
  FilterOutlined
} from '@ant-design/icons'
import CheckGroupCard from './CheckGroupCard'
import styles from './CheckListPanel.module.css'

/**
 * 筛选类型
 */
const FilterType = {
  ALL: 'all',
  ERROR: 'error',
  WARNING: 'warning'
}

/**
 * 默认核对分组数据
 */
const defaultCheckGroups = [
  {
    id: 'basic',
    name: '报告基础核对',
    icon: <FileTextOutlined />,
    items: [
      { code: 'C01', name: '首页与第三页一致性', status: 'pass', description: '委托方、样品名称、型号规格一致性核对' },
      { code: 'C02', name: '第三页扩展字段', status: 'pass', description: '型号规格、生产日期、产品编号/批号、商标、生产单位一致性核对' },
      { code: 'C03', name: '生产日期格式', status: 'pass', description: '表格与标签格式一致性核对' },
      { code: 'C04', name: '样品描述表格', status: 'pass', description: '各部件字段与标签比对' }
    ]
  },
  {
    id: 'photo',
    name: '样品照片核对',
    icon: <PictureOutlined />,
    items: [
      { code: 'C05', name: '样品照片数量', status: 'pass', description: '首页照片数量与实物照片数量核对' },
      { code: 'C06', name: '样品照片一致性', status: 'pass', description: '照片内容与描述一致性核对' }
    ]
  },
  {
    id: 'inspection',
    name: '检验项目核对',
    icon: <ExperimentOutlined />,
    items: [
      { code: 'C07', name: '单项结论核对', status: 'pass', description: '单项结论与综合结论一致性核对' },
      { code: 'C08', name: '非空字段核对', status: 'pass', description: '标准要求、检验结果、单项结论非空核对' },
      { code: 'C09', name: '产品编号/批号', status: 'pass', description: '检验项目与首页产品编号/批号一致性核对' },
      { code: 'C10', name: '续检标记核对', status: 'pass', description: '续检项目标记与结论一致性核对' }
    ]
  },
  {
    id: 'page',
    name: '页码校验',
    icon: <NumberOutlined />,
    items: [
      { code: 'C11', name: '页码连续性', status: 'pass', description: '报告页码连续性与总页数核对' }
    ]
  }
]

/**
 * CheckListPanel 组件
 * @param {Object} props
 * @param {Array} props.checkGroups - 核对分组数据（可选，默认使用defaultCheckGroups）
 * @param {Function} props.onItemClick - 点击核对项回调
 */
export default function CheckListPanel({ checkGroups = defaultCheckGroups, onItemClick }) {
  const [filter, setFilter] = useState(FilterType.ALL)

  /**
   * 根据筛选条件过滤核对项
   */
  const filteredGroups = useMemo(() => {
    if (filter === FilterType.ALL) {
      return checkGroups
    }

    return checkGroups.map(group => ({
      ...group,
      items: group.items.filter(item => {
        if (filter === FilterType.ERROR) {
          return item.status === 'fail' || item.errorCount > 0
        }
        if (filter === FilterType.WARNING) {
          return item.status === 'warning' || item.warningCount > 0
        }
        return true
      })
    })).filter(group => group.items.length > 0)
  }, [checkGroups, filter])

  /**
   * 计算统计数据
   */
  const stats = useMemo(() => {
    let total = 0
    let passed = 0
    let failed = 0
    let warnings = 0

    checkGroups.forEach(group => {
      group.items.forEach(item => {
        total++
        if (item.status === 'pass') passed++
        if (item.status === 'fail') failed++
        if (item.status === 'warning') warnings++
      })
    })

    return { total, passed, failed, warnings }
  }, [checkGroups])

  /**
   * 计算筛选后的统计
   */
  const filteredStats = useMemo(() => {
    let count = 0
    filteredGroups.forEach(group => {
      count += group.items.length
    })
    return { count }
  }, [filteredGroups])

  /**
   * 动画配置
   */
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: [0.34, 1.56, 0.64, 1]
      }
    }
  }

  return (
    <div className={styles.checkListPanel}>
      {/* 面板头部 */}
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <h2 className={styles.panelTitle}>核对内容清单</h2>
          <div className={styles.statsSummary}>
            <span className={styles.statItem}>
              <Badge count={stats.total} className={styles.statBadge} showZero />
              <span className={styles.statLabel}>总计</span>
            </span>
            {stats.passed > 0 && (
              <span className={styles.statItem}>
                <Badge count={stats.passed} className={`${styles.statBadge} ${styles.passBadge}`} showZero />
                <span className={styles.statLabel}>通过</span>
              </span>
            )}
            {stats.failed > 0 && (
              <span className={styles.statItem}>
                <Badge count={stats.failed} className={`${styles.statBadge} ${styles.failBadge}`} showZero />
                <span className={styles.statLabel}>失败</span>
              </span>
            )}
            {stats.warnings > 0 && (
              <span className={styles.statItem}>
                <Badge count={stats.warnings} className={`${styles.statBadge} ${styles.warningBadge}`} showZero />
                <span className={styles.statLabel}>警告</span>
              </span>
            )}
          </div>
        </div>

        {/* 筛选控件 */}
        <div className={styles.filterSection}>
          <FilterOutlined className={styles.filterIcon} />
          <Radio.Group
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className={styles.filterGroup}
            optionType="button"
            buttonStyle="solid"
            size="small"
          >
            <Radio.Button value={FilterType.ALL}>
              全部
              <span className={styles.filterCount}>{stats.total}</span>
            </Radio.Button>
            <Radio.Button value={FilterType.ERROR}>
              仅错误
              {stats.failed > 0 && <span className={styles.filterCount}>{stats.failed}</span>}
            </Radio.Button>
            <Radio.Button value={FilterType.WARNING}>
              仅警告
              {stats.warnings > 0 && <span className={styles.filterCount}>{stats.warnings}</span>}
            </Radio.Button>
          </Radio.Group>
        </div>
      </div>

      {/* 分组列表 */}
      <motion.div
        className={styles.groupsContainer}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {filteredGroups.length > 0 ? (
          filteredGroups.map((group) => (
            <motion.div key={group.id} variants={itemVariants}>
              <CheckGroupCard
                id={group.id}
                name={group.name}
                icon={group.icon}
                items={group.items}
              />
            </motion.div>
          ))
        ) : (
          <motion.div
            className={styles.emptyContainer}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span className={styles.emptyText}>
                  {filter === FilterType.ERROR
                    ? '未发现错误项'
                    : filter === FilterType.WARNING
                      ? '未发现警告项'
                      : '暂无核对项'}
                </span>
              }
            />
          </motion.div>
        )}
      </motion.div>

      {/* 底部汇总 */}
      {filteredGroups.length > 0 && (
        <div className={styles.panelFooter}>
          <div className={styles.footerProgress}>
            <div className={styles.progressBarBg}>
              <motion.div
                className={styles.progressBarFill}
                initial={{ width: 0 }}
                animate={{ width: `${(stats.passed / stats.total) * 100}%` }}
                transition={{ duration: 1, delay: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
              />
            </div>
            <span className={styles.progressText}>
              总体通过率: {stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0}%
              {filter !== FilterType.ALL && (
                <span className={styles.filteredHint}>（已筛选: {filteredStats.count} 项）</span>
              )}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
