/**
 * Result Components (New) - 重构后的结果页面组件
 * 使用新的设计系统和CSS变量
 */

export { default as CheckResult } from './CheckResult'
export { default as CheckListPanel } from './CheckListPanel'
export { default as CheckGroupCard } from './CheckGroupCard'
export { default as CheckItemCard } from './CheckItemCard'
export { default as InspectionTable } from './InspectionTable'
export { default as IssuesPanel } from './IssuesPanel'
export { default as DashboardStats } from './DashboardStats'
export { default as FileCard } from './FileCard'
export { default as PageCheckSection } from './PageCheckSection'
export { default as ComparisonTable, HomeThirdComparison, TableOcrComparison } from './ComparisonTable'

// 核对项详情组件
export {
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
