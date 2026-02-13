import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, TagOutlined, PictureOutlined } from '@ant-design/icons'
import DataTable from '../../ui/DataTable'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C06: 中文标签覆盖检查详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件中文标签数据
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 部件总数
 * @param {number} props.labeledComponents - 有中文标签的部件数
 * @param {Function} props.onPreviewLabel - 预览标签回调
 */
function C06ChineseLabelDetail({
  components = [],
  passed = true,
  totalComponents = 0,
  labeledComponents = 0,
  onPreviewLabel,
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 默认展示数据
  const defaultData = [
    {
      key: '1',
      componentName: '主机',
      labelStatus: 'has_label',
      isUnused: false,
      labelPhotoUrl: '/placeholder/label1.jpg',
      labelPhotoId: 'label1',
    },
    {
      key: '2',
      componentName: '推车',
      labelStatus: 'has_label',
      isUnused: false,
      labelPhotoUrl: '/placeholder/label2.jpg',
      labelPhotoId: 'label2',
    },
    {
      key: '3',
      componentName: '附件A',
      labelStatus: 'no_label',
      isUnused: false,
      labelPhotoUrl: null,
      labelPhotoId: null,
    },
    {
      key: '4',
      componentName: '附件B',
      labelStatus: 'unused',
      isUnused: true,
      labelPhotoUrl: null,
      labelPhotoId: null,
    },
  ]

  const dataSource = components.length > 0 ? components : defaultData

  const columns = [
    {
      title: '部件名称',
      dataIndex: 'componentName',
      key: 'componentName',
      width: '35%',
      render: (text, record) => (
        <div className="check-detail__component-cell">
          <TagOutlined className="check-detail__component-icon" />
          <span className="check-detail__component-name">{text}</span>
          {record.isUnused && (
            <StatusBadge status="warning" text="本次检测未使用" size="sm" />
          )}
        </div>
      ),
    },
    {
      title: '标签状态',
      dataIndex: 'labelStatus',
      key: 'labelStatus',
      width: '25%',
      align: 'center',
      render: (status, record) => {
        if (record.isUnused) {
          return (
            <StatusBadge
              status="warning"
              text="未使用"
              icon={<WarningOutlined />}
              size="sm"
            />
          )
        }
        return (
          <StatusBadge
            status={status === 'has_label' ? 'success' : 'error'}
            text={status === 'has_label' ? '有中文标签' : '无中文标签'}
            icon={status === 'has_label' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            size="sm"
          />
        )
      },
    },
    {
      title: '照片预览',
      dataIndex: 'labelPhotoUrl',
      key: 'labelPhotoUrl',
      width: '40%',
      align: 'center',
      render: (url, record) => {
        if (!url) {
          return (
            <span className="check-detail__no-preview">
              {record.isUnused ? '-' : '无照片'}
            </span>
          )
        }
        return (
          <motion.div
            className="check-detail__photo-preview"
            whileHover={{ scale: 1.05 }}
            onClick={(e) => {
              e.stopPropagation()
              onPreviewLabel?.(record)
            }}
          >
            <div className="check-detail__photo-thumb">
              <PictureOutlined className="check-detail__photo-placeholder-icon" />
              <span className="check-detail__photo-label">中文标签样张</span>
            </div>
          </motion.div>
        )
      },
    },
  ]

  // 统计未检测到中文标签的部件
  const noLabelComponents = dataSource.filter(
    c => !c.isUnused && c.labelStatus !== 'has_label'
  )

  return (
    <div className="check-detail">
      <motion.div
        className="check-detail__header"
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
        whileTap={{ scale: 0.99 }}
      >
        <div className="check-detail__header-left">
          <motion.span
            className="check-detail__expand-icon"
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <DownOutlined />
          </motion.span>
          <span className="check-detail__title">中文标签覆盖详情</span>
        </div>
        <div className="check-detail__header-right">
          <span className="check-detail__summary">
            {labeledComponents || dataSource.filter(c => c.labelStatus === 'has_label').length}
            /{totalComponents || dataSource.filter(c => !c.isUnused).length} 有标签
          </span>
          <StatusBadge
            status={passed ? 'success' : 'error'}
            text={passed ? '全部有标签' : '存在缺失'}
            size="sm"
          />
        </div>
      </motion.div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="check-detail__content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <DataTable
              columns={columns}
              dataSource={dataSource}
              size="small"
              bordered={false}
              pagination={false}
            />

            {/* 未检测到中文标签的错误提示 */}
            {noLabelComponents.length > 0 && (
              <motion.div
                className="check-detail__error-list"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="check-detail__error-title">
                  <CloseCircleOutlined className="check-detail__error-icon" />
                  <span>以下部件未检测到中文标签：</span>
                </div>
                <div className="check-detail__error-items">
                  {noLabelComponents.map(component => (
                    <span key={component.key} className="check-detail__error-item">
                      {component.componentName}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}

            {/* 说明 */}
            <div className="check-detail__note">
              <span className="check-detail__note-label">说明:</span>
              <span className="check-detail__note-text">
                每个部件至少应有一张中文标签照片，"本次检测未使用"的部件除外。
                中文标签判定：说明文字包含"中文标签"、"中文标签样张"、"标签样张"等
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C06ChineseLabelDetail
