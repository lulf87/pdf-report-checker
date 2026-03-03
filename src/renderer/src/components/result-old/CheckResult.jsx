/**
 * CheckResult - 核对结果主组件
 * 科技感数据大屏设计系统
 * 整合所有结果展示子组件
 */

import React, { useMemo } from 'react'
import { Result, Typography } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import { FileTextOutlined, LoadingOutlined, PictureOutlined, AuditOutlined, FileOutlined } from '@ant-design/icons'
import { FileCard, IssuesPanel, InspectionTable, ComparisonTable, PageCheckSection, CheckListPanel } from './'
import { ActionBar } from '../ui'
import styles from './CheckResult.module.css'

// 导入核对项详情组件
import {
  C01HomeThirdDetail,
  C02ThirdPageExtendedDetail,
  C03DateFormatDetail,
  C04SampleTableDetail,
  C05PhotoCoverageDetail,
  C06ChineseLabelDetail,
  C07ConclusionDetail,
  C08NonEmptyFieldDetail,
  C09SerialNumberDetail,
  C10ContinuationMarkDetail,
  C11PageNumberDetail
} from './CheckItemDetail'

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
 * CheckResult - 核对结果主组件
 * @param {Object} props
 * @param {Object} props.fileInfo - 当前文件信息
 * @param {Object} props.result - 核对结果数据
 * @param {boolean} props.loading - 加载状态
 * @param {Function} props.onCheck - 核对回调
 * @param {Function} props.onReset - 重置回调
 * @param {boolean} props.llmEnabled - LLM是否启用
 * @param {Function} props.onLlmToggle - LLM切换回调
 * @param {string} props.apiBaseUrl - API基础URL
 */
function CheckResult({
  fileInfo,
  result,
  loading,
  onCheck,
  onReset,
  llmEnabled,
  onLlmToggle,
  apiBaseUrl
}) {
  // 将后端返回的核对结果数据转换为 checkGroups 格式
  const checkGroups = useMemo(() => {
    if (!result) return []

    // C01: 首页与第三页一致性
    const c01HomeThirdComparison = result?.home_third_comparison || []
    const c01ErrorCount = c01HomeThirdComparison.filter(i => !i.is_match).length

    // C02: 第三页扩展字段检查
    const c02ExtendedCheck = result?.third_page_extended_check || {}
    const c02Passed = c02ExtendedCheck?.passed ?? true
    const c02CheckType = c02ExtendedCheck?.check_type || 'field_compare'

    // C03: 生产日期格式检查
    const c03DateCheck = result?.date_format_check || {}
    const c03Passed = c03DateCheck?.passed ?? true

    // C04: 样品描述表格检查
    const c04SampleTableCheck = result?.sample_table_check || {}
    const c04Passed = c04SampleTableCheck?.passed ?? true
    const c04Components = c04SampleTableCheck?.components || []
    const c04ErrorCount = c04Components.filter(c => {
      const fields = c.fields || []
      return fields.some(f => f.status !== 'match')
    }).length

    // C05: 照片覆盖性检查
    const c05PhotoCheck = result?.photo_coverage_check || {}
    const c05Passed = c05PhotoCheck?.passed ?? true
    const c05Components = c05PhotoCheck?.components || []
    const c05UncoveredCount = c05Components.filter(c => !c.isUnused && c.status !== 'covered').length

    // C06: 中文标签覆盖检查
    const c06LabelCheck = result?.chinese_label_check || {}
    const c06Passed = c06LabelCheck?.passed ?? true
    const c06Components = c06LabelCheck?.components || []
    const c06NoLabelCount = c06Components.filter(c => !c.isUnused && c.labelStatus !== 'has_label').length

    // C07: 单项结论核对
    const c07InspectionCheck = result?.inspection_item_check || {}
    const c07Passed = c07InspectionCheck?.passed ?? true
    const c07IncorrectConclusions = c07InspectionCheck?.incorrect_conclusions || 0

    // C08: 非空字段校验
    const c08EmptyFieldErrors = (result?.errors || []).filter(e =>
      e.details?.error_code?.startsWith('EMPTY_FIELD_')
    ).length

    // C09: 序号连续性检查
    const c09SerialNumberErrors = (result?.errors || []).filter(e =>
      e.details?.error_code?.startsWith('SERIAL_NUMBER_ERROR_') ||
      e.details?.error_type === 'SERIAL_NUMBER_DISCONTINUITY'
    ).length

    // C10: 续表标记检查
    const c10ContinuationErrors = (result?.errors || []).filter(e =>
      e.details?.error_code?.startsWith('CONTINUATION_MARK_ERROR_') ||
      e.details?.error_type?.includes('CONTINUATION')
    ).length

    // C11: 页码连续性校验
    const c11PageCheck = result?.page_number_check || {}
    const c11Passed = c11PageCheck?.passed ?? true
    const c11ContinuityErrors = c11PageCheck?.continuity_errors || []

    return [
      {
        id: 'basic',
        name: '报告基础核对',
        icon: <FileTextOutlined />,
        items: [
          {
            code: 'C01',
            name: '首页与第三页一致性',
            status: c01ErrorCount === 0 ? 'pass' : 'fail',
            description: '委托方、样品名称、型号规格的跨页一致性校验',
            errorCount: c01ErrorCount,
            defaultExpanded: true,
            details: (
              <C01HomeThirdDetail
                comparisons={c01HomeThirdComparison.map(item => ({
                  key: item.field,
                  fieldName: item.field_label || item.field,
                  homeValue: item.home_value,
                  thirdPageValue: item.third_page_value,
                  status: item.is_match ? 'match' : 'mismatch'
                }))}
                passed={c01ErrorCount === 0}
              />
            )
          },
          {
            code: 'C02',
            name: '第三页扩展字段',
            status: c02Passed ? 'pass' : 'fail',
            description: '型号规格、生产日期、产品编号/批号、商标、生产单位一致性核对',
            errorCount: c02Passed ? 0 : 1,
            defaultExpanded: true,
            details: (
              <C02ThirdPageExtendedDetail
                comparisons={(c02ExtendedCheck?.comparisons || []).map(item => ({
                  key: item.field,
                  fieldName: item.field_label || item.field,
                  tableValue: item.table_value,
                  labelValue: item.label_value,
                  status: item.is_match ? 'match' : 'mismatch'
                }))}
                passed={c02Passed}
                checkType={c02CheckType}
              />
            )
          },
          {
            code: 'C03',
            name: '生产日期格式',
            status: c03Passed ? 'pass' : 'fail',
            description: '表格与标签格式一致性核对',
            errorCount: c03Passed ? 0 : 1,
            defaultExpanded: true,
            details: (
              <C03DateFormatDetail
                tableFormat={c03DateCheck?.table_format}
                labelFormat={c03DateCheck?.label_format}
                passed={c03Passed}
                tableDate={c03DateCheck?.table_date}
                labelDate={c03DateCheck?.label_date}
              />
            )
          },
          {
            code: 'C04',
            name: '样品描述表格',
            status: c04Passed ? 'pass' : 'fail',
            description: '各部件字段与标签比对',
            errorCount: c04ErrorCount,
            defaultExpanded: false,
            details: (
              <C04SampleTableDetail
                components={c04Components}
                passed={c04Passed}
                totalComponents={c04Components.length}
                passedComponents={c04Components.filter(c => {
                  const fields = c.fields || []
                  return fields.every(f => f.status === 'match')
                }).length}
              />
            )
          }
        ]
      },
      {
        id: 'photo',
        name: '样品照片核对',
        icon: <PictureOutlined />,
        items: [
          {
            code: 'C05',
            name: '照片覆盖性',
            status: c05Passed ? 'pass' : 'fail',
            description: '首页照片数量与实物照片数量核对',
            errorCount: c05UncoveredCount,
            defaultExpanded: false,
            details: (
              <C05PhotoCoverageDetail
                components={c05Components}
                passed={c05Passed}
                totalComponents={c05Components.filter(c => !c.isUnused).length}
                coveredComponents={c05Components.filter(c => !c.isUnused && c.status === 'covered').length}
              />
            )
          },
          {
            code: 'C06',
            name: '中文标签覆盖',
            status: c06Passed ? 'pass' : 'fail',
            description: '照片内容与描述一致性核对',
            errorCount: c06NoLabelCount,
            defaultExpanded: false,
            details: (
              <C06ChineseLabelDetail
                components={c06Components}
                passed={c06Passed}
                totalComponents={c06Components.filter(c => !c.isUnused).length}
                labeledComponents={c06Components.filter(c => !c.isUnused && c.labelStatus === 'has_label').length}
              />
            )
          }
        ]
      },
      {
        id: 'inspection',
        name: '检验项目核对',
        icon: <AuditOutlined />,
        items: [
          {
            code: 'C07',
            name: '单项结论核对',
            status: c07Passed ? 'pass' : 'fail',
            description: '单项结论与综合结论一致性核对',
            errorCount: c07IncorrectConclusions,
            defaultExpanded: false,
            details: (
              <C07ConclusionDetail data={c07InspectionCheck} />
            )
          },
          {
            code: 'C08',
            name: '非空字段校验',
            status: c08EmptyFieldErrors === 0 ? 'pass' : 'fail',
            description: '标准要求、检验结果、单项结论非空核对',
            errorCount: c08EmptyFieldErrors,
            defaultExpanded: false,
            details: (
              <C08NonEmptyFieldDetail data={c07InspectionCheck} />
            )
          },
          {
            code: 'C09',
            name: '序号连续性',
            status: c09SerialNumberErrors === 0 ? 'pass' : 'warning',
            description: '检验项目与首页产品编号/批号一致性核对',
            errorCount: c09SerialNumberErrors,
            defaultExpanded: false,
            details: (
              <C09SerialNumberDetail
                data={{
                  errors: result?.errors || [],
                  serial_numbers: c07InspectionCheck?.serial_numbers || []
                }}
              />
            )
          },
          {
            code: 'C10',
            name: '续表标记',
            status: c10ContinuationErrors === 0 ? 'pass' : 'warning',
            description: '续检项目标记与结论一致性核对',
            errorCount: c10ContinuationErrors,
            defaultExpanded: false,
            details: (
              <C10ContinuationMarkDetail
                data={{
                  errors: result?.errors || [],
                  continuation_marks: c07InspectionCheck?.continuation_marks || [],
                  cross_page_continuations: c07InspectionCheck?.cross_page_continuations || 0
                }}
              />
            )
          }
        ]
      },
      {
        id: 'page',
        name: '页码校验',
        icon: <FileOutlined />,
        items: [
          {
            code: 'C11',
            name: '页码连续性',
            status: c11Passed ? 'pass' : 'fail',
            description: '报告页码连续性与总页数核对',
            errorCount: c11ContinuityErrors.length,
            defaultExpanded: false,
            details: (
              <C11PageNumberDetail data={c11PageCheck} />
            )
          }
        ]
      }
    ]
  }, [result])

  // 导出处理
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
      console.error('导出失败:', error)
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
          <FileCard fileInfo={fileInfo} />
        </motion.div>

        <motion.div variants={itemVariants}>
          <Result
            icon={
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                <FileTextOutlined style={{ color: 'var(--color-neon-blue)', fontSize: 72, filter: 'drop-shadow(0 0 20px rgba(59, 130, 246, 0.5))' }} />
              </motion.div>
            }
            title={
              <span style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
                文件已上传
              </span>
            }
            subTitle={
              <span style={{ color: 'var(--text-secondary)' }}>
                {fileInfo?.filename} 准备就绪，点击下方按钮开始核对
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
            <LoadingOutlined style={{ fontSize: 48, color: 'var(--color-neon-blue)', filter: 'drop-shadow(0 0 15px rgba(59, 130, 246, 0.5))' }} />
          </motion.div>
          <div className={styles.loadingText}>
            <Text style={{ fontSize: 18, fontWeight: 500, color: 'var(--text-primary)' }}>正在核对报告，请稍候...</Text>
          </div>
          <div className={styles.loadingSubtext}>
            <Text style={{ color: 'var(--text-secondary)' }}>包括：PDF解析、OCR识别、字段比对等步骤</Text>
          </div>

          {/* 进度条动画 */}
          <div style={{ width: 256, margin: '24px auto 0' }}>
            <motion.div
              style={{
                height: 4,
                background: 'rgba(59, 130, 246, 0.2)',
                borderRadius: 2,
                overflow: 'hidden'
              }}
            >
              <motion.div
                style={{
                  height: '100%',
                  background: 'linear-gradient(90deg, var(--color-neon-blue) 0%, var(--color-neon-cyan) 100%)',
                  borderRadius: 2,
                  boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)'
                }}
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
      {/* 文件信息卡片 */}
      <motion.div variants={itemVariants}>
        <FileCard fileInfo={fileInfo} onExport={handleExport} />
      </motion.div>

      {/* 核对清单面板 */}
      <motion.div variants={itemVariants}>
        <CheckListPanel checkGroups={checkGroups} />
      </motion.div>

      {/* 问题汇总面板 */}
      <motion.div variants={itemVariants}>
        <IssuesPanel
          errors={result?.errors || []}
          warnings={result?.warnings || []}
          info={result?.info || []}
        />
      </motion.div>

      {/* 检验项目表格 */}
      <motion.div variants={itemVariants}>
        <InspectionTable data={result?.inspection_item_check} />
      </motion.div>

      {/* 字段比对表格 */}
      <motion.div variants={itemVariants}>
        <ComparisonTable data={result?.home_third_comparison || []} />
      </motion.div>

      {/* 页码校验区域 */}
      <motion.div variants={itemVariants}>
        <PageCheckSection data={result?.page_number_check} />
      </motion.div>

      {/* 底部操作栏 */}
      <motion.div variants={itemVariants}>
        <ActionBar
          onCheck={onCheck}
          onReset={onReset}
          onExportPdf={() => handleExport('pdf')}
          onExportExcel={() => handleExport('excel')}
          llmEnabled={llmEnabled}
          onLlmToggle={onLlmToggle}
          showExport={true}
        />
      </motion.div>
    </motion.div>
  )
}

export default CheckResult
