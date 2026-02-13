import React from 'react'
import { Card, Space, Typography, Button, Dropdown, Tooltip } from 'antd'
import {
  FileTextOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 文件信息卡片组件
 * @param {Object} props
 * @param {Object} props.fileInfo - 文件信息对象
 * @param {string} props.fileInfo.filename - 文件名
 * @param {string} props.fileInfo.file_type - 文件类型
 * @param {Function} [props.onExport] - 导出回调函数
 */
function FileInfoCard({ fileInfo, onExport }) {
  const exportMenuItems = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: '导出 PDF 报告',
      onClick: () => onExport?.('pdf'),
    },
    {
      key: 'excel',
      icon: <FileExcelOutlined />,
      label: '导出 Excel 表格',
      onClick: () => onExport?.('excel'),
    },
  ]

  return (
    <Card size="small" className={styles.fileInfoCard}>
      <div className={styles.fileInfoContent}>
        <Space size="middle">
          <div className={styles.fileIcon}>
            <FileTextOutlined />
          </div>
          <div>
            <div className={styles.fileName}>{fileInfo.filename}</div>
            <Text type="secondary" className={styles.fileType}>
              类型: {fileInfo.file_type?.toUpperCase?.() || '未知'}
            </Text>
          </div>
        </Space>

        {onExport && (
          <Dropdown
            menu={{ items: exportMenuItems }}
            placement="bottomRight"
          >
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              className={styles.exportButton}
            >
              导出报告
            </Button>
          </Dropdown>
        )}
      </div>
    </Card>
  )
}

export default FileInfoCard
