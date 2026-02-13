import React from 'react'
import { Spin, Result, Typography } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import { FileTextOutlined, LoadingOutlined } from '@ant-design/icons'
import FileInfoCard from './FileInfoCard'
import DashboardStats from './DashboardStats'
import IssuesPanel from './IssuesPanel'
import ComparisonSection from './ComparisonSection'
import SampleTableSection from './SampleTableSection'
import ComponentsSection from './ComponentsSection'
import ActionBar from './ActionBar'
// v2.1/v2.2 新增组件
import InspectionItemSection from './InspectionItemSection'
import ThirdPageExtendedSection from './ThirdPageExtendedSection'
import PageNumberCheckSection from './PageNumberCheckSection'
import styles from './styles.module.css'

const { Text } = Typography

// 动画配置
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
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
      duration: 0.5,
      ease: [0.34, 1.56, 0.64, 1]
    }
  }
}

const loadingVariants = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 }
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    transition: { duration: 0.2 }
  }
}

/**
 * CheckResult 组件 - 报告核对结果展示
 */
function CheckResult({
  fileInfo,
  result,
  loading,
  onCheck,
  onReset,
  llmEnabled,
  onLlmToggle,
  apiBaseUrl,
}) {
  // 导出报告
  const handleExport = async (format) => {
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/export/${fileInfo.file_id}?format=${format}`
      )

      if (!response.ok) {
        throw new Error('导出失败')
      }

      // 获取文件名
      const contentDisposition = response.headers.get('content-disposition')
      let filename = `核对报告.${format === 'excel' ? 'xlsx' : format}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/)
        if (match) {
          filename = match[1]
        }
      }

      // 下载文件
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      throw error
    }
  }

  // 未开始核对状态
  if (!result && !loading) {
    return (
      <motion.div
        className={styles.container}
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        <motion.div variants={itemVariants}>
          <FileInfoCard fileInfo={fileInfo} />
        </motion.div>

        <motion.div variants={itemVariants}>
          <Result
            icon={
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                <FileTextOutlined style={{ color: '#3b82f6', fontSize: 72 }} />
              </motion.div>
            }
            title={
              <span className="text-xl font-semibold text-slate-800">
                文件已上传
              </span>
            }
            subTitle={
              <span className="text-slate-500">
                {fileInfo.filename} 准备就绪，点击下方按钮开始核对
              </span>
            }
            extra={
              <ActionBar
                onCheck={onCheck}
                onReset={onReset}
                llmEnabled={llmEnabled}
                onLlmToggle={onLlmToggle}
                showExport={false}
              />
            }
          />
        </motion.div>
      </motion.div>
    )
  }

  // 加载中状态
  if (loading) {
    return (
      <AnimatePresence>
        <motion.div
          className={styles.loadingContainer}
          variants={loadingVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <motion.div
            animate={{
              rotate: 360,
              transition: { duration: 2, repeat: Infinity, ease: 'linear' }
            }}
          >
            <LoadingOutlined style={{ fontSize: 48, color: '#3b82f6' }} />
          </motion.div>
          <div className={styles.loadingText}>
            <Text className="text-lg font-medium">正在核对报告，请稍候...</Text>
          </div>
          <div className={styles.loadingSubtext}>
            <Text type="secondary">包括：PDF解析、OCR识别、字段比对等步骤</Text>
          </div>

          {/* 进度条动画 */}
          <div className="w-64 mx-auto mt-6">
            <motion.div
              className="h-1 bg-medical-100 rounded-full overflow-hidden"
            >
              <motion.div
                className="h-full bg-gradient-to-r from-medical-400 to-medical-600 rounded-full"
                initial={{ width: '0%' }}
                animate={{
                  width: ['0%', '30%', '60%', '80%', '90%'],
                  transition: {
                    duration: 8,
                    times: [0, 0.2, 0.5, 0.8, 1],
                    repeat: Infinity
                  }
                }}
              />
            </motion.div>
          </div>
        </motion.div>
      </AnimatePresence>
    )
  }

  // 核对结果展示
  return (
    <motion.div
      className={styles.container}
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <motion.div variants={itemVariants}>
        <FileInfoCard fileInfo={fileInfo} onExport={handleExport} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <DashboardStats result={result} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <IssuesPanel
          errors={result.errors || []}
          warnings={result.warnings || []}
          info={result.info || []}
        />
      </motion.div>

      {/* v2.1 新增：检验项目核对 */}
      <motion.div variants={itemVariants}>
        <InspectionItemSection data={result.inspection_item_check} />
      </motion.div>

      {/* v2.2 新增：第三页扩展字段核对 */}
      <motion.div variants={itemVariants}>
        <ThirdPageExtendedSection data={result.third_page_extended_checks} />
      </motion.div>

      {/* v2.2 新增：页码连续性校验 */}
      <motion.div variants={itemVariants}>
        <PageNumberCheckSection data={result.page_number_check} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <ComparisonSection data={result.home_third_comparison || []} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <SampleTableSection data={result.sample_description_table} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <ComponentsSection components={result.component_checks || []} />
      </motion.div>

      <motion.div variants={itemVariants}>
        <ActionBar
          onCheck={onCheck}
          onReset={onReset}
          onExport={handleExport}
          llmEnabled={llmEnabled}
          onLlmToggle={onLlmToggle}
          showExport={true}
        />
      </motion.div>
    </motion.div>
  )
}

export default CheckResult
