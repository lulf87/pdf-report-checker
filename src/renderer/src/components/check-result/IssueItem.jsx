import React from 'react'
import classNames from 'classnames'
import { Typography } from 'antd'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 单个问题项组件
 * @param {Object} props
 * @param {Object} props.item - 问题对象
 * @param {string} props.item.message - 问题消息
 * @param {number} [props.item.page_num] - 页码
 * @param {string} props.type - 类型: 'error' | 'warning' | 'info'
 * @param {React.ReactNode} props.icon - 图标
 */
function IssueItem({ item, type, icon }) {
  return (
    <div className={classNames(styles.issueItem, styles[type])}>
      <span className={classNames(styles.issueItemIcon, styles[type])}>
        {icon}
      </span>
      <div className={styles.issueItemContent}>
        <div className={styles.issueItemMessage}>{item.message}</div>
        {item.page_num && (
          <Text type="secondary" className={styles.issueItemMeta}>
            页码: {item.page_num}
          </Text>
        )}
      </div>
    </div>
  )
}

export default IssueItem
