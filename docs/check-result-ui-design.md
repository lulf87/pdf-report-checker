# 报告核对结果展示界面设计方案

## 一、设计理念

### 整体风格
- **专业医疗感**：以白色为基底，搭配医疗蓝（Medical Blue）作为主色调，传达专业、可靠、洁净的视觉感受
- **现代化呼吸感**：使用柔和阴影、圆角、充足留白，摆脱传统医疗软件的沉重感
- **信息层级清晰**：通过卡片分区、色彩编码、字体大小建立明确的信息层级

### 设计原则
1. **一目了然**：关键信息（通过/失败状态）在首屏即可见，无需滚动
2. **问题优先**：失败项和警告项优先展示，支持快速定位
3. **减少点击**：避免使用 Tabs 隐藏信息，改用折叠面板（Collapse）和卡片分区
4. **视觉反馈**：状态变化有明确的色彩+图标双重标识

---

## 二、色彩系统 (Design Tokens)

```javascript
// tailwind.config.js 扩展
colors: {
  medical: {
    50: '#f0f7ff',
    100: '#e0effe',
    500: '#3b82f6',  // 主色：医疗蓝
    600: '#2563eb',
    700: '#1d4ed8',
  },
  status: {
    pass: '#10b981',      // 通过：翠绿
    passBg: '#d1fae5',
    fail: '#ef4444',      // 失败：警示红
    failBg: '#fee2e2',
    warn: '#f59e0b',      // 警告：琥珀
    warnBg: '#fef3c7',
    info: '#6b7280',      // 信息：中性灰
    infoBg: '#f3f4f6',
  },
  surface: {
    primary: '#ffffff',
    secondary: '#f8fafc',
    tertiary: '#f1f5f9',
  }
}
```

---

## 三、布局结构

### 整体布局（从上到下）

```
┌─────────────────────────────────────────────────────────────┐
│  [Header] 文件信息卡片 + 导出按钮                            │
├─────────────────────────────────────────────────────────────┤
│  [Dashboard] 总体结果摘要（统计卡片行）                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ 总部件  │ │  通过   │ │  失败   │ │ 通过率  │          │
│  │   24    │ │   20    │ │    4    │ │  83.3%  │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
├─────────────────────────────────────────────────────────────┤
│  [问题汇总面板] 错误/警告/信息（可折叠，默认展开错误）       │
├─────────────────────────────────────────────────────────────┤
│  [首页与第三页比对] 表格形式，不一致项高亮                   │
├─────────────────────────────────────────────────────────────┤
│  [样品描述表格] 表格形式，视觉优化                           │
├─────────────────────────────────────────────────────────────┤
│  [部件核对区域] 卡片网格布局                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [筛选器] 全部 | 通过 | 失败 | 警告                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │ │ 部件A       │ │ 部件B       │ │ 部件C       │    │   │
│  │ │ [状态标签]  │ │ [状态标签]  │ │ [状态标签]  │    │   │
│  │ │             │ │             │ │             │    │   │
│  │ │ [折叠内容]  │ │ [折叠内容]  │ │ [折叠内容]  │    │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  [Footer] 重新核对 | 导出报告 | 上传新文件                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、组件详细设计

### 1. 总体结果摘要 (DashboardStats)

**布局**：4列统计卡片，使用 CSS Grid

```jsx
// 组件结构
<div className="grid grid-cols-4 gap-4 mb-6">
  <StatCard
    title="总部件数"
    value={24}
    icon={<AppstoreOutlined />}
    color="medical"
  />
  <StatCard
    title="通过"
    value={20}
    icon={<CheckCircleOutlined />}
    color="pass"
    trend="+2"
  />
  <StatCard
    title="失败"
    value={4}
    icon={<CloseCircleOutlined />}
    color="fail"
  />
  <StatCard
    title="通过率"
    value="83.3%"
    icon={<PieChartOutlined />}
    color="medical"
    suffix=""
  />
</div>
```

**样式代码 (Tailwind)**：
```css
/* StatCard 组件样式 */
.stat-card {
  @apply relative overflow-hidden rounded-xl bg-white p-5
         shadow-sm border border-slate-100
         transition-all duration-300 ease-out
         hover:shadow-md hover:-translate-y-0.5;
}

.stat-card::before {
  @apply absolute left-0 top-0 h-full w-1 content-'';
}

.stat-card.pass::before { @apply bg-emerald-500; }
.stat-card.fail::before { @apply bg-red-500; }
.stat-card.medical::before { @apply bg-blue-500; }

.stat-card-icon {
  @apply absolute right-4 top-4 text-3xl opacity-20;
}

.stat-card-value {
  @apply text-3xl font-bold tracking-tight text-slate-800;
}

.stat-card-title {
  @apply mt-1 text-sm font-medium text-slate-500;
}
```

---

### 2. 问题汇总面板 (IssuesPanel)

**布局**：可折叠面板，使用 Ant Design Collapse 组件

```jsx
<Collapse
  defaultActiveKey={['errors']}
  className="issues-panel"
  items={[
    {
      key: 'errors',
      label: (
        <div className="flex items-center gap-2">
          <Badge count={errors.length} className="error-badge" />
          <span className="font-medium">错误</span>
          <span className="text-slate-400 text-sm">需立即处理</span>
        </div>
      ),
      children: <IssuesList issues={errors} type="error" />,
    },
    {
      key: 'warnings',
      label: (
        <div className="flex items-center gap-2">
          <Badge count={warnings.length} className="warning-badge" />
          <span className="font-medium">警告</span>
        </div>
      ),
      children: <IssuesList issues={warnings} type="warning" />,
    },
  ]}
/>
```

**样式代码**：
```css
.issues-panel {
  @apply mb-6 rounded-xl border border-slate-200 overflow-hidden;
}

.issues-panel .ant-collapse-header {
  @apply bg-slate-50 hover:bg-slate-100 transition-colors;
}

.error-badge .ant-badge-count {
  @apply bg-red-500;
}

.warning-badge .ant-badge-count {
  @apply bg-amber-500;
}

.issue-item {
  @apply flex items-start gap-3 p-3 rounded-lg
         hover:bg-slate-50 transition-colors cursor-pointer;
}

.issue-item.error {
  @apply border-l-4 border-red-500 bg-red-50/50;
}

.issue-item.warning {
  @apply border-l-4 border-amber-500 bg-amber-50/50;
}
```

---

### 3. 首页与第三页比对 (ComparisonTable)

**布局**：表格形式，不一致行高亮

```jsx
<Card
  title="首页与第三页比对"
  className="comparison-section mb-6"
  extra={
    <Tag color={allMatch ? 'success' : 'error'}>
      {allMatch ? '全部一致' : `${mismatchCount} 处不一致`}
    </Tag>
  }
>
  <Table
    columns={comparisonColumns}
    dataSource={homeThirdComparison}
    rowClassName={(record) => !record.is_match ? 'row-mismatch' : ''}
    pagination={false}
    size="middle"
  />
</Card>
```

**样式代码**：
```css
.comparison-section {
  @apply rounded-xl shadow-sm border border-slate-200;
}

.comparison-section .ant-card-head {
  @apply bg-slate-50 border-b border-slate-100;
}

.comparison-section .ant-table {
  @apply rounded-lg overflow-hidden;
}

/* 不一致行高亮 */
.row-mismatch {
  @apply bg-red-50/60 !important;
}

.row-mismatch td {
  @apply text-red-700 font-medium;
}

/* 状态标签样式 */
.status-tag {
  @apply inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium;
}

.status-tag.match {
  @apply bg-emerald-100 text-emerald-700;
}

.status-tag.mismatch {
  @apply bg-red-100 text-red-700;
}
```

---

### 4. 部件核对卡片 (ComponentCard)

**布局**：卡片网格，每个部件独立卡片，可展开

```jsx
// 卡片头部
<div className="component-card-header">
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-3">
      <div className={cn("status-indicator", status)} />
      <span className="font-semibold text-slate-800">{componentName}</span>
    </div>
    <StatusTag status={status} />
  </div>

  {/* 快速信息行 */}
  <div className="flex items-center gap-4 mt-3 text-sm">
    <QuickInfo
      icon={<CameraOutlined />}
      label="照片"
      value={hasPhoto ? '有' : '无'}
      status={hasPhoto ? 'pass' : 'fail'}
    />
    <QuickInfo
      icon={<TagOutlined />}
      label="中文标签"
      value={hasLabel ? '有' : '无'}
      status={hasLabel ? 'pass' : 'fail'}
    />
    <QuickInfo
      icon={<FileTextOutlined />}
      label="字段比对"
      value={`${matchCount}/${totalFields}`}
      status={allMatch ? 'pass' : 'fail'}
    />
  </div>
</div>

// 折叠内容
<div className="component-card-body">
  {/* 匹配的照片 */}
  {matchedPhotos.length > 0 && (
    <PhotoGallery photos={matchedPhotos} />
  )}

  {/* 字段比对表格 */}
  <FieldComparisonTable comparisons={fieldComparisons} />

  {/* 问题列表 */}
  {issues.length > 0 && (
    <IssuesList issues={issues} compact />
  )}
</div>
```

**样式代码**：
```css
.component-card {
  @apply rounded-xl border border-slate-200 bg-white
         shadow-sm transition-all duration-300
         hover:shadow-md;
}

.component-card.fail {
  @apply border-red-200;
}

.component-card.warn {
  @apply border-amber-200;
}

.component-card-header {
  @apply p-4 cursor-pointer;
}

.status-indicator {
  @apply w-2.5 h-2.5 rounded-full;
}

.status-indicator.pass { @apply bg-emerald-500; }
.status-indicator.fail { @apply bg-red-500; }
.status-indicator.warn { @apply bg-amber-500; }

.quick-info {
  @apply flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs;
}

.quick-info.pass {
  @apply bg-emerald-50 text-emerald-700;
}

.quick-info.fail {
  @apply bg-red-50 text-red-700;
}

.component-card-body {
  @apply px-4 pb-4 border-t border-slate-100;
}

/* 字段比对表格 - 紧凑版 */
.field-table {
  @apply mt-3 text-sm;
}

.field-table th {
  @apply bg-slate-50 text-slate-600 font-medium py-2 px-3 text-left;
}

.field-table td {
  @apply py-2 px-3 border-b border-slate-100;
}

.field-table .mismatch {
  @apply bg-red-50/50 text-red-700;
}
```

---

### 5. 筛选器 (FilterBar)

```jsx
<div className="filter-bar">
  <span className="text-sm text-slate-500">筛选：</span>
  <Radio.Group
    value={filter}
    onChange={setFilter}
    optionType="button"
    buttonStyle="solid"
    options={[
      { label: `全部 (${total})`, value: 'all' },
      { label: `通过 (${passed})`, value: 'pass' },
      { label: `失败 (${failed})`, value: 'fail' },
      { label: `警告 (${warned})`, value: 'warn' },
    ]}
  />
</div>
```

**样式代码**：
```css
.filter-bar {
  @apply flex items-center gap-3 mb-4 p-3 bg-slate-50 rounded-lg;
}

.filter-bar .ant-radio-button-wrapper {
  @apply border-slate-200;
}

.filter-bar .ant-radio-button-wrapper-checked {
  @apply bg-medical-500 border-medical-500;
}
```

---

## 五、组件拆分建议

将 `CheckResult.jsx` (513行) 拆分为以下组件：

```
src/renderer/src/components/check-result/
├── index.jsx                    # 主入口，整合所有子组件
├── FileInfoCard.jsx             # 文件信息卡片
├── DashboardStats.jsx           # 统计摘要面板
│   └── StatCard.jsx             # 单个统计卡片
├── IssuesPanel.jsx              # 问题汇总面板
│   └── IssueItem.jsx            # 单个问题项
├── ComparisonSection.jsx        # 首页与第三页比对
├── SampleTableSection.jsx       # 样品描述表格
├── ComponentsSection.jsx        # 部件核对区域
│   ├── FilterBar.jsx            # 筛选器
│   ├── ComponentCard.jsx        # 单个部件卡片
│   ├── FieldComparisonTable.jsx # 字段比对表格
│   └── PhotoGallery.jsx         # 照片展示
└── ActionBar.jsx                # 底部操作栏
```

### 主入口组件结构

```jsx
// CheckResult/index.jsx
function CheckResult({ fileInfo, result, loading, ...props }) {
  if (!result && !loading) return <EmptyState {...props} />;
  if (loading) return <LoadingState />;

  return (
    <div className="check-result-container">
      <FileInfoCard fileInfo={fileInfo} />
      <DashboardStats result={result} />
      <IssuesPanel issues={result.issues} />
      <ComparisonSection data={result.home_third_comparison} />
      <SampleTableSection data={result.sample_description_table} />
      <ComponentsSection components={result.component_checks} />
      <ActionBar onReset={props.onReset} onExport={handleExport} />
    </div>
  );
}
```

---

## 六、响应式布局

```css
/* 移动端适配 */
@media (max-width: 768px) {
  .dashboard-stats {
    @apply grid-cols-2;
  }

  .component-grid {
    @apply grid-cols-1;
  }

  .filter-bar {
    @apply flex-wrap;
  }

  .filter-bar .ant-radio-group {
    @apply w-full mt-2;
  }
}

/* 平板适配 */
@media (min-width: 769px) and (max-width: 1024px) {
  .component-grid {
    @apply grid-cols-2;
  }
}

/* 桌面端 */
@media (min-width: 1025px) {
  .component-grid {
    @apply grid-cols-2 xl:grid-cols-3;
  }
}
```

---

## 七、微交互设计

### 1. 卡片悬停效果
```css
.component-card {
  @apply transition-all duration-300 ease-out;
}

.component-card:hover {
  @apply -translate-y-1 shadow-lg;
}
```

### 2. 状态切换动画
```css
.status-indicator {
  @apply transition-colors duration-300;
}

.status-tag {
  @apply transition-all duration-200;
}

.status-tag:hover {
  @apply scale-105;
}
```

### 3. 表格行高亮过渡
```css
.row-mismatch {
  @apply transition-colors duration-200;
}

.row-mismatch:hover {
  @apply bg-red-100;
}
```

### 4. 折叠面板动画
```css
.component-card-body {
  @apply transition-all duration-300 ease-in-out;
}
```

---

## 八、Ant Design 主题定制

```javascript
// theme.js - ConfigProvider 配置
export const theme = {
  token: {
    // 主色调
    colorPrimary: '#3b82f6',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',

    // 圆角
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,

    // 阴影
    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
    boxShadowSecondary: '0 4px 6px -1px rgb(0 0 0 / 0.1)',

    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
  },
  components: {
    Card: {
      headerBg: '#f8fafc',
      headerFontSize: 16,
    },
    Table: {
      headerBg: '#f8fafc',
      rowHoverBg: '#f1f5f9',
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Button: {
      borderRadius: 8,
    },
  },
};
```

---

## 九、关键改进点总结

| 原设计问题 | 新设计方案 |
|-----------|-----------|
| Tabs 隐藏信息 | 改为卡片分区 + 折叠面板，信息一目了然 |
| 513行单文件 | 拆分为9个组件，职责单一 |
| 部件核对嵌套过深 | 卡片网格布局，快速信息行展示关键状态 |
| 缺乏整体总结 | 顶部 Dashboard 统计卡片 |
| 问题列表分散 | 统一问题汇总面板，支持分级折叠 |
| 导出按钮不显眼 | 移至顶部文件信息卡片旁 |
| 视觉风格陈旧 | 现代化卡片设计，柔和阴影，呼吸感留白 |

---

## 十、实现优先级

1. **P0 - 核心结构**：DashboardStats + 组件拆分
2. **P1 - 视觉优化**：Card 样式、色彩系统、表格样式
3. **P2 - 交互增强**：筛选器、折叠动画、悬停效果
4. **P3 - 响应式**：移动端适配
