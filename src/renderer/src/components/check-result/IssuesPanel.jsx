import React from 'react'
import { Collapse, Badge, List, Typography, Empty } from 'antd'
import {
  WarningOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import IssueItem from './IssueItem'
import styles from './styles.module.css'

const { Text } = Typography
const { Panel } = Collapse

/**
 * 问题汇总面板组件
 * @param {Object} props
 * @param {Array} props.errors - 错误列表
 * @param {Array} props.warnings - 警告列表
 * @param {Array} props.info - 信息列表
 */
function IssuesPanel({ errors = [], warnings = [], info = [] }) {
  const hasErrors = errors.length > 0
  const hasWarnings = warnings.length > 0
  const hasInfo = info.length > 0

  if (!hasErrors && !hasWarnings && !hasInfo) {
    return (
      <div className={styles.issuesPanelEmpty}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="未发现任何问题"
        />
      </div>
    )
  }

  const collapseItems = []

  if (hasErrors) {
    collapseItems.push({
      key: 'errors',
      label: (
        <div className={styles.issuesPanelHeader}>
          <Badge count={errors.length} className={styles.errorBadge} />
          <span className={styles.issuesPanelTitle}>错误</span>
          <span className={styles.issuesPanelSubtitle}>需立即处理</span>
        </div>
      ),
      children: (
        <List
          dataSource={errors}
          renderItem={(item, index) => (
            <IssueItem
              key={index}
              item={item}
              type="error"
              icon={<CloseCircleOutlined />}
            />
          )}
        />
      ),
    })
  }

  if (hasWarnings) {
    collapseItems.push({
      key: 'warnings',
      label: (
        <div className={styles.issuesPanelHeader}>
          <Badge count={warnings.length} className={styles.warningBadge} />
          <span className={styles.issuesPanelTitle}>警告</span>
        </div>
      ),
      children: (
        <List
          dataSource={warnings}
          renderItem={(item, index) => (
            <IssueItem
              key={index}
              item={item}
              type="warning"
              icon={<WarningOutlined />}
            />
          )}
        />
      ),
    })
  }

  if (hasInfo) {
    collapseItems.push({
      key: 'info',
      label: (
        <div className={styles.issuesPanelHeader}>
          <Badge count={info.length} className={styles.infoBadge} />
          <span className={styles.issuesPanelTitle}>信息</span>
        </div>
      ),
      children: (
        <List
          dataSource={info}
          renderItem={(item, index) => (
            <IssueItem
              key={index}
              item={item}
              type="info"
              icon={<InfoCircleOutlined />}
            />
          )}
        />
      ),
    })
  }

  return (
    <Collapse
      defaultActiveKey={hasErrors ? ['errors'] : []}
      className={styles.issuesPanel}
      items={collapseItems}
    />
  )
}

export default IssuesPanel
