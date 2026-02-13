import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DownOutlined, CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, EyeOutlined, CameraOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import DataTable from '../../ui/DataTable'
import StatusBadge from '../../ui/StatusBadge'
import './CheckItemDetail.css'

/**
 * C05: 照片覆盖性检查结果详情组件
 * @param {Object} props
 * @param {Array} props.components - 部件照片覆盖数据
 * @param {boolean} props.passed - 是否通过
 * @param {number} props.totalComponents - 部件总数
 * @param {number} props.coveredComponents - 有照片覆盖的部件数
 * @param {Function} props.onViewPhoto - 查看照片回调
 */
function C05PhotoCoverageDetail({
  components = [],
  passed = true,
  totalComponents = 0,
  coveredComponents = 0,
  onViewPhoto,
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 默认展示数据
  const defaultData = [
    {
      key: '1',
      componentName: '主机',
      photoCount: 3,
      status: 'covered',
      isUnused: false,
      photoIds: ['photo1', 'photo2', 'photo3'],
    },
    {
      key: '2',
      componentName: '推车',
      photoCount: 2,
      status: 'covered',
      isUnused: false,
      photoIds: ['photo4', 'photo5'],
    },
    {
      key: '3',
      componentName: '附件A',
      photoCount: 0,
      status: 'uncovered',
      isUnused: false,
      photoIds: [],
    },
    {
      key: '4',
      componentName: '附件B',
      photoCount: 0,
      status: 'unused',
      isUnused: true,
      photoIds: [],
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
          <CameraOutlined className="check-detail__component-icon" />
          <span className="check-detail__component-name">{text}</span>
          {record.isUnused && (
            <StatusBadge status="warning" text="本次检测未使用" size="sm" />
          )}
        </div>
      ),
    },
    {
      title: '照片数量',
      dataIndex: 'photoCount',
      key: 'photoCount',
      width: '20%',
      align: 'center',
      render: (count, record) => (
        <span className={`check-detail__photo-count ${record.status}`}>
          {count} 张
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
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
            status={status === 'covered' ? 'success' : 'error'}
            text={status === 'covered' ? '已覆盖' : '未覆盖'}
            icon={status === 'covered' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            size="sm"
          />
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: '20%',
      align: 'center',
      render: (_, record) => (
        record.photoCount > 0 && (
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onViewPhoto?.(record)
            }}
            className="check-detail__view-btn"
          >
            查看照片
          </Button>
        )
      ),
    },
  ]

  // 统计未覆盖的部件
  const uncoveredComponents = dataSource.filter(
    c => !c.isUnused && c.status !== 'covered'
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
          <span className="check-detail__title">照片覆盖详情</span>
        </div>
        <div className="check-detail__header-right">
          <span className="check-detail__summary">
            {coveredComponents || dataSource.filter(c => c.status === 'covered').length}
            /{totalComponents || dataSource.filter(c => !c.isUnused).length} 已覆盖
          </span>
          <StatusBadge
            status={passed ? 'success' : 'error'}
            text={passed ? '全部覆盖' : '存在未覆盖'}
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

            {/* 未覆盖部件错误提示 */}
            {uncoveredComponents.length > 0 && (
              <motion.div
                className="check-detail__error-list"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="check-detail__error-title">
                  <CloseCircleOutlined className="check-detail__error-icon" />
                  <span>以下部件缺少照片覆盖：</span>
                </div>
                <div className="check-detail__error-items">
                  {uncoveredComponents.map(component => (
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
                每个部件至少应有一张照片覆盖，"本次检测未使用"的部件除外
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default C05PhotoCoverageDetail
