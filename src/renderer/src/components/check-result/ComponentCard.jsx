import React, { useState } from 'react'
import classNames from 'classnames'
import { Card, Tag, Space, Collapse, Typography, Alert } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  CameraOutlined,
  TagOutlined,
  FileTextOutlined,
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons'
import FieldComparisonTable from './FieldComparisonTable'
import PhotoGallery from './PhotoGallery'
import styles from './styles.module.css'

const { Text } = Typography
const { Panel } = Collapse

/**
 * 快速信息行组件
 * @param {Object} props
 * @param {React.ReactNode} props.icon - 图标
 * @param {string} props.label - 标签
 * @param {string} props.value - 值
 * @param {string} props.status - 状态: 'pass' | 'fail'
 */
function QuickInfo({ icon, label, value, status }) {
  return (
    <div className={classNames(styles.quickInfo, styles[status])}>
      {icon}
      <span>{label}:</span>
      <span className={styles.quickInfoValue}>{value}</span>
    </div>
  )
}

/**
 * 状态标签组件
 * @param {Object} props
 * @param {string} props.status - 状态: 'pass' | 'fail' | 'warn'
 */
function StatusTag({ status }) {
  const config = {
    pass: { color: 'success', icon: <CheckCircleOutlined />, text: '通过' },
    fail: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
    warn: { color: 'warning', icon: <WarningOutlined />, text: '警告' },
  }

  const { color, icon, text } = config[status] || config.warn

  return (
    <Tag color={color} icon={icon} className={styles.componentStatusTag}>
      {text}
    </Tag>
  )
}

/**
 * 单个部件卡片组件
 * @param {Object} props
 * @param {Object} props.component - 部件数据
 */
function ComponentCard({ component }) {
  const [expanded, setExpanded] = useState(false)

  const {
    component_name,
    status,
    has_photo,
    has_chinese_label,
    matched_photos = [],
    matched_labels = [],
    field_comparisons = [],
    issues = [],
    match_reason,
  } = component

  const matchCount = field_comparisons.filter((f) => f.is_match).length
  const totalFields = field_comparisons.length
  const allFieldsMatch = totalFields > 0 && matchCount === totalFields

  const collapseItems = []

  if (matched_photos.length > 0) {
    collapseItems.push({
      key: 'photos',
      label: (
        <span>
          <CameraOutlined /> 匹配的照片 ({matched_photos.length}张)
        </span>
      ),
      children: <PhotoGallery photos={matched_photos} />,
    })
  }

  if (field_comparisons.length > 0) {
    collapseItems.push({
      key: 'fields',
      label: (
        <span>
          <FileTextOutlined /> 字段比对 ({matchCount}/{totalFields})
        </span>
      ),
      children: <FieldComparisonTable comparisons={field_comparisons} />,
    })
  }

  return (
    <Card
      className={classNames(styles.componentCard, styles[status])}
      bodyStyle={{ padding: 0 }}
    >
      {/* 卡片头部 */}
      <div
        className={styles.componentCardHeader}
        onClick={() => setExpanded(!expanded)}
      >
        <div className={styles.componentCardHeaderTop}>
          <div className={styles.componentCardTitle}>
            <div className={classNames(styles.statusIndicator, styles[status])} />
            <span className={styles.componentName}>{component_name}</span>
          </div>
          <div className={styles.componentCardHeaderRight}>
            <StatusTag status={status} />
            {expanded ? <DownOutlined /> : <RightOutlined />}
          </div>
        </div>

        {/* 快速信息行 */}
        <div className={styles.quickInfoRow}>
          <QuickInfo
            icon={<CameraOutlined />}
            label="照片"
            value={has_photo ? '有' : '无'}
            status={has_photo ? 'pass' : 'fail'}
          />
          <QuickInfo
            icon={<TagOutlined />}
            label="中文标签"
            value={has_chinese_label ? '有' : '无'}
            status={has_chinese_label ? 'pass' : 'fail'}
          />
          {totalFields > 0 && (
            <QuickInfo
              icon={<FileTextOutlined />}
              label="字段比对"
              value={`${matchCount}/${totalFields}`}
              status={allFieldsMatch ? 'pass' : 'fail'}
            />
          )}
        </div>
      </div>

      {/* 折叠内容 */}
      {expanded && (
        <div className={styles.componentCardBody}>
          {collapseItems.length > 0 && (
            <Collapse
              ghost
              defaultActiveKey={['fields']}
              items={collapseItems}
              className={styles.componentCollapse}
            />
          )}

          {match_reason && (
            <div className={styles.matchReason}>
              <Text type="secondary">{match_reason}</Text>
            </div>
          )}

          {issues.length > 0 && (
            <Alert
              message="问题"
              description={
                <ul className={styles.issuesList}>
                  {issues.map((issue, idx) => (
                    <li key={idx}>{issue}</li>
                  ))}
                </ul>
              }
              type={status === 'fail' ? 'error' : 'warning'}
              showIcon
              className={styles.componentIssuesAlert}
            />
          )}
        </div>
      )}
    </Card>
  )
}

export default ComponentCard
