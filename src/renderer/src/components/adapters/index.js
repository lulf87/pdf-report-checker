/**
 * adapters - API适配器统一导出
 *
 * 适配器层用于确保新旧组件API的向后兼容性。
 * 当新组件API有变更时，通过适配器将旧版props转换为新版props。
 *
 * 使用方式:
 * import { CheckItemCardAdapter, StatCardAdapter } from './adapters'
 *
 * // 使用旧版API调用新组件
 * <CheckItemCardAdapter
 *   code="C01"
 *   name="首页与第三页一致性"
 *   status="pass"
 *   errorCount={0}
 *   warningCount={0}
 *   defaultExpanded={false}
 * />
 */

export { default as CheckItemCardAdapter } from './CheckItemCardAdapter'
export { default as StatCardAdapter } from './StatCardAdapter'
export { default as UploadZoneAdapter } from './UploadZoneAdapter'
export { default as FileCardAdapter } from './FileCardAdapter'

// 默认导出所有适配器
export { default } from './CheckItemCardAdapter'
