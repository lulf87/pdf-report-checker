import React, { useState, useMemo } from 'react'
import { Card, Radio, Empty, Typography } from 'antd'
import ComponentCard from './ComponentCard'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 部件核对区域组件
 * @param {Object} props
 * @param {Array} props.components - 部件核对数据数组
 */
function ComponentsSection({ components = [] }) {
  const [filter, setFilter] = useState('all')

  const stats = useMemo(() => {
    const total = components.length
    const passed = components.filter((c) => c.status === 'pass').length
    const failed = components.filter((c) => c.status === 'fail').length
    const warned = components.filter((c) => c.status === 'warn').length
    return { total, passed, failed, warned }
  }, [components])

  const filteredComponents = useMemo(() => {
    if (filter === 'all') return components
    return components.filter((c) => c.status === filter)
  }, [components, filter])

  if (components.length === 0) {
    return (
      <Card title="部件核对" className={styles.componentsSection}>
        <Empty description="无部件核对数据" />
      </Card>
    )
  }

  const filterOptions = [
    { label: `全部 (${stats.total})`, value: 'all' },
    { label: `通过 (${stats.passed})`, value: 'pass' },
    { label: `失败 (${stats.failed})`, value: 'fail' },
    { label: `警告 (${stats.warned})`, value: 'warn' },
  ]

  return (
    <Card
      title={
        <div className={styles.componentsSectionTitle}>
          <span>部件核对</span>
          <Text type="secondary" className={styles.componentsSectionSubtitle}>
            共 {stats.total} 个部件
          </Text>
        </div>
      }
      className={styles.componentsSection}
    >
      <div className={styles.filterBar}>
        <Text type="secondary">筛选：</Text>
        <Radio.Group
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          options={filterOptions}
          size="small"
        />
      </div>

      {filteredComponents.length === 0 ? (
        <Empty description={`无${filter === 'pass' ? '通过' : filter === 'fail' ? '失败' : '警告'}的部件`} />
      ) : (
        <div className={styles.componentGrid}>
          {filteredComponents.map((component, index) => (
            <ComponentCard key={index} component={component} />
          ))}
        </div>
      )}
    </Card>
  )
}

export default ComponentsSection
