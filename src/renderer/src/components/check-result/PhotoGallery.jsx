import React from 'react'
import { Tag, Space, Typography } from 'antd'
import { PictureOutlined } from '@ant-design/icons'
import styles from './styles.module.css'

const { Text } = Typography

/**
 * 照片展示组件
 * @param {Object} props
 * @param {Array} props.photos - 照片数据数组
 * @param {number} props.photos[].page_num - 页码
 * @param {string} [props.photos[].caption] - 标题
 */
function PhotoGallery({ photos = [] }) {
  if (photos.length === 0) {
    return null
  }

  return (
    <div className={styles.photoGallery}>
      <Space size={[8, 8]} wrap>
        {photos.map((photo, idx) => (
          <Tag
            key={idx}
            color="blue"
            icon={<PictureOutlined />}
            className={styles.photoTag}
          >
            第{photo.page_num}页
            {photo.caption && (
              <span className={styles.photoCaption}>: {photo.caption}</span>
            )}
          </Tag>
        ))}
      </Space>
    </div>
  )
}

export default PhotoGallery
