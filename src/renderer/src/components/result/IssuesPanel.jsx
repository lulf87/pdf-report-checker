/**
 * IssuesPanel - 问题汇总面板 (重构版)
 * 使用新的设计系统和CSS变量
 */

import React from 'react'
import { Collapse, Badge, List, Empty } from 'antd'
import {
  WarningOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import styles from './IssuesPanel.module.css'

/**
 * 问题项组件
 */
function IssueItem({ item, type, icon }) {
  return (
    <div className={`${styles.issueItem} ${styles[type]}`}>
      <div className={`${styles.issueItemIcon} ${styles[type]}`}>
        {icon}
      </div>
      <div className={styles.issueItemContent}>
        <div className={styles.issueItemMessage}>{item.message || item}</div>
        {item.field && (
          <div className={styles.issueItemMeta}>字段: {item.field}</div>
        )}
      </div>
    </div>
  )
}

/**
 * 问题汇总面板组件
 * @param {Object} props
 * @param {Array} props.errors - 错误列表
 * @param {Array} props.warnings - 警告列表
 * @param {Array} props.info - 信息列表
 */
export default function IssuesPanel({ errors = [], warnings = [], info = [] }) {
  const hasErrors = errors.length > 0
  const hasWarnings = warnings.length > 0
  const hasInfo = info.length > 0

  if (!hasErrors && !hasWarnings && !hasInfo) {
    return (
      <div className={styles.issuesPanelEmpty}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span className={styles.emptyText}>未发现任何问题</span>}
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
    <div className={styles.issuesPanelWrapper}>
      <div className={styles.issuesPanelHeader}>
        <h3 className={styles.panelTitle}>问题汇总</h3>
        <div className={styles.badgeGroup}>
          {hasErrors && (
            <span className={`${styles.countBadge} ${styles.error}`}>
              <CloseCircleOutlined /> {errors.length}
            </span>
          )}
          {hasWarnings && (
            <span className={`${styles.countBadge} ${styles.warning}`}>
              <WarningOutlined /> {warnings.length}
            </span>
          )}
          {hasInfo && (
            <span className={`${styles.countBadge} ${styles.info}`}>
              <InfoCircleOutlined /> {info.length}
            </span>
          )}
        </div>
      </div>
      <Collapse
        defaultActiveKey={hasErrors ? ['errors'] : []}
        className={styles.issuesPanel}
        items={collapseItems}
        expandIconPosition="end"
      />
    </div>
  )
}
