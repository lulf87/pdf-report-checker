# 报告核对工具 - 全新UI系统架构设计规范

> **版本**: v2.1
> **日期**: 2026-02-13
> **目标**: 专业、现代、高效的医疗检验报告核对桌面应用

---

## 1. 设计哲学

### 1.1 核心原则

- **专业性**: 医疗场景需要严谨、可信赖的视觉语言，避免过度娱乐化的霓虹效果
- **可读性**: 数据密集型界面，信息层级清晰，快速准确地阅读数据
- **效率**: 减少视觉干扰，聚焦核心任务，支持长时间工作
- **一致性**: 统一的交互模式，降低学习成本

### 1.2 设计关键词

`专业` `清晰` `现代` `可信` `高效` `医疗` `数据` `严谨`

### 1.3 与现有组件的关系

本设计规范与以下现有组件保持一致：
- `OptimizedCard` - 优化版卡片组件
- `OptimizedBackground` - 轻量级背景组件
- `design-system.css` - 现有设计系统样式

---

## 2. 色彩系统

### 2.1 设计原则

基于调研报告建议，采用以下色彩策略：
- **避免纯黑色**: 使用深蓝灰 `#0f172a` (slate-900) 作为主背景，减少视觉疲劳
- **柔和白色文字**: 使用 `#f9fafb` 而非纯白，避免眩光
- **降低饱和度**: 强调色使用柔和版本，避免"振动"效果

### 2.2 主色调

| Token | Hex | RGB | 用途 |
|-------|-----|-----|------|
| `--color-primary` | `#3B82F6` | rgb(59, 130, 246) | 主品牌色、主要操作 |
| `--color-primary-light` | `#60A5FA` | rgb(96, 165, 250) | 悬停状态、强调 |
| `--color-primary-dark` | `#2563EB` | rgb(37, 99, 235) | 按下状态 |
| `--color-secondary` | `#06B6D4` | rgb(6, 182, 212) | 次要操作、信息提示 |
| `--color-accent` | `#8B5CF6` | rgb(139, 92, 246) | 强调色、高亮 |

### 2.3 深色主题背景色

采用深蓝灰而非纯黑，提升可读性和专业感：

| Token | Hex | 用途 |
|-------|-----|------|
| `--bg-primary` | `#0A0E17` | 主背景色（深蓝灰）- 接近现有实现 |
| `--bg-secondary` | `#111827` | 卡片背景、次级容器 |
| `--bg-tertiary` | `#1F2937` | 悬停背景、分隔区域 |
| `--bg-elevated` | `#1A2332` | 浮层、弹窗背景 |
| `--bg-card` | `rgba(17, 24, 39, 0.85)` | 玻璃效果卡片背景 |
| `--bg-input` | `#0F172A` | 输入框背景 |

### 2.4 状态色

| 状态 | Token | Hex | 用途 |
|------|-------|-----|------|
| 成功 | `--color-success` | `#10B981` | 通过、完成、正常 |
| 成功亮 | `--color-success-light` | `#34D399` | 成功状态悬停 |
| 警告 | `--color-warning` | `#F59E0B` | 警告、需注意 |
| 警告亮 | `--color-warning-light` | `#FBBF24` | 警告状态悬停 |
| 错误 | `--color-error` | `#EF4444` | 错误、失败、阻断 |
| 错误亮 | `--color-error-light` | `#F87171` | 错误状态悬停 |
| 信息 | `--color-info` | `#6B7280` | 提示、说明 |

### 2.5 文字颜色

| Token | Hex | 用途 |
|-------|-----|------|
| `--text-primary` | `#F9FAFB` | 主要文字（标题、正文）- 柔和白 |
| `--text-secondary` | `#D1D5DB` | 次要文字（描述、标签） |
| `--text-tertiary` | `#9CA3AF` | 辅助文字（占位符、禁用） |
| `--text-muted` | `#6B7280` | 弱化文字（时间、元数据） |
| `--text-inverse` | `#1F2937` | 反色文字（用于亮色背景） |

### 2.6 边框与分隔

| Token | Hex | 用途 |
|-------|-----|------|
| `--border-subtle` | `rgba(59, 130, 246, 0.1)` | 微弱分隔 |
| `--border-default` | `rgba(59, 130, 246, 0.2)` | 默认边框 |
| `--border-strong` | `rgba(59, 130, 246, 0.3)` | 强调边框 |
| `--border-focus` | `#3B82F6` | 聚焦状态 |

---

## 3. 字体系统

### 3.1 字体选择

采用双字体策略：专业正文字体 + 数据展示等宽字体

```css
/* 字体栈 */
--font-sans: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', Consolas, monospace;
```

**字体说明**:
- **Inter**: 现代无衬线字体，专为屏幕阅读优化，数字清晰
- **JetBrains Mono**: 等宽字体，用于代码、编号、数值等需要对齐的内容

### 3.2 字体导入

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

### 3.3 字体大小规范

| Token | 大小 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| `--text-xs` | 12px | 16px | 400 | 标签、徽章文字 |
| `--text-sm` | 14px | 20px | 400 | 辅助文字、说明、表格内容 |
| `--text-base` | 16px | 24px | 400 | 正文、按钮 |
| `--text-lg` | 18px | 28px | 500 | 小标题、强调 |
| `--text-xl` | 20px | 30px | 600 | 卡片标题 |
| `--text-2xl` | 24px | 32px | 600 | 区块标题 |
| `--text-3xl` | 30px | 40px | 700 | 页面标题 |

### 3.4 字重规范

| Token | 值 | 用途 |
|-------|-----|------|
| `--font-normal` | 400 | 正文 |
| `--font-medium` | 500 | 按钮、标签 |
| `--font-semibold` | 600 | 标题、强调 |
| `--font-bold` | 700 | 大标题、关键数据 |

---

## 4. 间距系统

### 4.1 基础间距

| Token | 值 | 用途 |
|-------|-----|------|
| `--space-xs` | 4px | 紧凑间距、图标间隙 |
| `--space-sm` | 8px | 小间距、内联元素 |
| `--space-md` | 16px | 标准间距、卡片内边距 |
| `--space-lg` | 24px | 大间距、区块间距 |
| `--space-xl` | 32px | 大区块间距 |
| `--space-2xl` | 48px | 页面间距 |

### 4.2 组件间距

| 场景 | 值 | 说明 |
|------|-----|------|
| 卡片内边距 | 16px - 20px | 根据卡片大小调整 |
| 按钮内边距 | 8px 16px | 标准按钮 |
| 输入框高度 | 40px | 统一高度 |
| 表格行高 | 48px | 数据行 |
| 列表项间距 | 8px | 紧凑列表 |
| 表单字段间距 | 16px | 垂直间距 |

---

## 5. 布局网格

### 5.1 桌面应用栅格

- **容器最大宽度**: 1440px
- **列数**: 12列
- **列间距**: 24px
- **边距**: 32px（大屏）/ 24px（中屏）/ 16px（小屏）

### 5.2 断点定义

| 断点 | 宽度 | 说明 |
|------|------|------|
| `sm` | 640px | 小屏 |
| `md` | 768px | 平板 |
| `lg` | 1024px | 小桌面 |
| `xl` | 1280px | 标准桌面 |
| `2xl` | 1440px | 大桌面 |

### 5.3 页面布局结构

```
┌─────────────────────────────────────────────────────────┐
│  Header (56px)                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │              Main Content Area                  │   │
│  │                                                 │   │
│  │   ┌─────────────┐  ┌───────────────────────┐   │   │
│  │   │   Sidebar   │  │      Content          │   │   │
│  │   │   (280px)   │  │      (flex: 1)        │   │   │
│  │   └─────────────┘  └───────────────────────┘   │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Footer (40px)                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 圆角系统

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | 4px | 小元素、标签、输入框 |
| `--radius-md` | 8px | 按钮、小卡片 |
| `--radius-lg` | 12px | 卡片、弹窗 |
| `--radius-xl` | 16px | 大卡片、模态框 |
| `--radius-full` | 9999px | 圆形、胶囊形、徽章 |

---

## 7. 阴影系统

### 7.1 深色主题阴影

深色主题下阴影使用带颜色的阴影，增强层次感：

| Token | 值 | 用途 |
|-------|-----|------|
| `--shadow-sm` | `0 1px 2px rgba(0, 0, 0, 0.3)` | 轻微提升 |
| `--shadow-md` | `0 4px 6px rgba(0, 0, 0, 0.4)` | 卡片 |
| `--shadow-lg` | `0 10px 15px rgba(0, 0, 0, 0.5)` | 浮层 |
| `--shadow-glow-sm` | `0 0 10px rgba(59, 130, 246, 0.2)` | 蓝色发光效果 |
| `--shadow-glow-md` | `0 0 20px rgba(59, 130, 246, 0.3)` | 强蓝色发光 |
| `--shadow-glow-success` | `0 0 10px rgba(16, 185, 129, 0.3)` | 成功发光 |
| `--shadow-glow-error` | `0 0 10px rgba(239, 68, 68, 0.3)` | 错误发光 |

---

## 8. 组件规范

### 8.1 按钮 (Button)

#### 主按钮 (Primary)

```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #3B82F6;
  color: white;
  cursor: pointer;
  transition: all 150ms ease;
  white-space: nowrap;
}

.btn-primary:hover {
  background: #2563EB;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
}

.btn-primary:active {
  transform: scale(0.98);
}

.btn-primary:focus-visible {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}
```

#### 次按钮 (Secondary)

```css
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: #1F2937;
  color: #F9FAFB;
  cursor: pointer;
  transition: all 150ms ease;
}

.btn-secondary:hover {
  border-color: #3B82F6;
  color: #60A5FA;
}
```

#### 幽灵按钮 (Ghost)

```css
.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #D1D5DB;
  cursor: pointer;
  transition: all 150ms ease;
}

.btn-ghost:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #60A5FA;
}
```

#### 成功/危险按钮

```css
.btn-success {
  background: #10B981;
  color: white;
}

.btn-success:hover {
  background: #059669;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}

.btn-error {
  background: #EF4444;
  color: white;
}

.btn-error:hover {
  background: #DC2626;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
}
```

#### 图标按钮 (Icon Button)

```css
.btn-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #9CA3AF;
  cursor: pointer;
  transition: all 150ms ease;
}

.btn-icon:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3B82F6;
  color: #F9FAFB;
}
```

### 8.2 卡片 (Card)

#### 标准卡片

```css
.card {
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 12px;
  padding: 16px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
  contain: layout style paint;
}

.card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
}
```

#### 可交互卡片

```css
.card-interactive {
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 150ms ease;
}

.card-interactive:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 10px rgba(59, 130, 246, 0.2);
}

.card-interactive:active {
  transform: translateY(0);
}
```

#### 带左侧边框强调的卡片

```css
.card-accent {
  position: relative;
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 12px;
  padding: 16px;
  padding-left: 19px; /* 16px + 3px border */
  transition: border-color 150ms ease;
}

.card-accent::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #3B82F6;
  border-radius: 12px 0 0 12px;
}

.card-accent--success::before { background: #10B981; }
.card-accent--warning::before { background: #F59E0B; }
.card-accent--error::before { background: #EF4444; }
.card-accent--info::before { background: #6B7280; }
```

#### 玻璃效果卡片

```css
.card-glass {
  background: rgba(17, 24, 39, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.card-glass:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
}

/* 降级方案 - 不使用 backdrop-filter */
.card-glass-fallback {
  background: #151d2a;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
}
```

#### 文件卡片

```css
.card-file {
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-file__icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3B82F6;
  font-size: 24px;
}

.card-file__info {
  flex: 1;
}

.card-file__name {
  font-weight: 500;
  color: #F9FAFB;
  font-size: 14px;
}

.card-file__meta {
  color: #6B7280;
  font-size: 12px;
  margin-top: 4px;
}
```

#### 统计卡片

```css
.stat-card {
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  padding: 16px;
  position: relative;
  overflow: hidden;
  transition: border-color 150ms ease;
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 3px;
  background: #3B82F6;
}

.stat-card--blue::before { background: #3B82F6; }
.stat-card--green::before { background: #10B981; }
.stat-card--red::before { background: #EF4444; }
.stat-card--amber::before { background: #F59E0B; }
.stat-card--purple::before { background: #8B5CF6; }

.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  color: #F9FAFB;
  line-height: 1;
  font-family: 'JetBrains Mono', monospace;
}

.stat-card__label {
  font-size: 12px;
  color: #9CA3AF;
  margin-top: 4px;
}
```

#### 核对项卡片

```css
.card-check {
  background: #111827;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 150ms ease;
}

.card-check:hover {
  border-color: rgba(59, 130, 246, 0.3);
  background: #1a2332;
}

.card-check--pass {
  border-left: 3px solid #10B981;
}

.card-check--fail {
  border-left: 3px solid #EF4444;
}

.card-check--warning {
  border-left: 3px solid #F59E0B;
}

.card-check__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-check__code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #6B7280;
  background: rgba(15, 23, 42, 0.5);
  padding: 2px 8px;
  border-radius: 4px;
}

.card-check__title {
  font-weight: 500;
  color: #F9FAFB;
  font-size: 14px;
  margin-top: 8px;
}

.card-check__desc {
  color: #9CA3AF;
  font-size: 12px;
  margin-top: 4px;
}
```

### 8.3 状态标签 (Status Tag)

```css
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid transparent;
  white-space: nowrap;
}

.status-tag--success {
  background: rgba(16, 185, 129, 0.1);
  color: #34D399;
  border-color: rgba(16, 185, 129, 0.2);
}

.status-tag--warning {
  background: rgba(245, 158, 11, 0.1);
  color: #FBBF24;
  border-color: rgba(245, 158, 11, 0.2);
}

.status-tag--error {
  background: rgba(239, 68, 68, 0.1);
  color: #F87171;
  border-color: rgba(239, 68, 68, 0.2);
}

.status-tag--info {
  background: rgba(59, 130, 246, 0.1);
  color: #60A5FA;
  border-color: rgba(59, 130, 246, 0.2);
}

.status-tag--neutral {
  background: rgba(107, 114, 128, 0.1);
  color: #9CA3AF;
  border-color: rgba(107, 114, 128, 0.2);
}
```

### 8.4 表格 (Table)

#### 数据表格

```css
.data-table-container {
  overflow-x: auto;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 12px;
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
}

.data-table th {
  background: rgba(59, 130, 246, 0.08);
  color: #F9FAFB;
  font-weight: 600;
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  white-space: nowrap;
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  color: #D1D5DB;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: rgba(59, 130, 246, 0.05);
}
```

#### 带状态行的表格

```css
.data-table tr.error td {
  background: rgba(239, 68, 68, 0.05);
  color: #F87171;
}

.data-table tr.error:hover td {
  background: rgba(239, 68, 68, 0.08);
}

.data-table tr.warning td {
  background: rgba(245, 158, 11, 0.05);
}

.data-table tr.success td {
  background: rgba(16, 185, 129, 0.05);
}
```

### 8.5 输入框 (Input)

```css
.input {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  color: #F9FAFB;
  background: #1F2937;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.input::placeholder {
  color: #6B7280;
}

.input:hover {
  border-color: rgba(59, 130, 246, 0.3);
}

.input:focus {
  outline: none;
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

### 8.6 拖拽上传区域 (Upload Zone)

```css
.upload-zone {
  border: 2px dashed rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 48px 32px;
  text-align: center;
  background: transparent;
  transition: all 150ms ease;
  cursor: pointer;
}

.upload-zone:hover {
  border-color: #3B82F6;
  background: rgba(59, 130, 246, 0.03);
}

.upload-zone--dragover {
  border-color: #3B82F6;
  background: rgba(59, 130, 246, 0.08);
}

.upload-zone__icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3B82F6;
  font-size: 28px;
}

.upload-zone__title {
  font-size: 16px;
  font-weight: 500;
  color: #F9FAFB;
}

.upload-zone__hint {
  font-size: 14px;
  color: #6B7280;
  margin-top: 8px;
}
```

### 8.7 步骤条 (Steps)

```css
.steps {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step__indicator {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.step--pending .step__indicator {
  background: #111827;
  border: 2px solid rgba(59, 130, 246, 0.3);
  color: #6B7280;
}

.step--active .step__indicator {
  background: #3B82F6;
  color: #FFFFFF;
}

.step--completed .step__indicator {
  background: #10B981;
  color: #FFFFFF;
}

.step__label {
  font-size: 14px;
  color: #D1D5DB;
}

.step__divider {
  width: 32px;
  height: 2px;
  background: rgba(59, 130, 246, 0.2);
}

.step__divider--completed {
  background: #10B981;
}
```

### 8.8 标签页 (Tabs)

```css
.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: #0F172A;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.1);
}

.tab {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #9CA3AF;
  cursor: pointer;
  transition: all 150ms ease;
  border: none;
  background: transparent;
}

.tab:hover {
  color: #D1D5DB;
}

.tab--active {
  background: #111827;
  color: #F9FAFB;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.tab__count {
  margin-left: 6px;
  padding: 2px 8px;
  background: rgba(107, 114, 128, 0.2);
  border-radius: 9999px;
  font-size: 11px;
}
```

### 8.9 进度条 (Progress Bar)

```css
.progress-bar {
  height: 6px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: linear-gradient(90deg, #3B82F6 0%, #06B6D4 100%);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-bar--success .progress-bar__fill {
  background: #10B981;
}

.progress-bar--error .progress-bar__fill {
  background: #EF4444;
}
```

### 8.10 分隔线 (Divider)

```css
.divider {
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(59, 130, 246, 0.2) 50%,
    transparent 100%
  );
  margin: 16px 0;
}

.divider-vertical {
  width: 1px;
  height: 100%;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(59, 130, 246, 0.2) 50%,
    transparent 100%
  );
}
```

---

## 9. 动效规范

### 9.1 过渡时间

| Token | 值 | 用途 |
|-------|-----|------|
| `--transition-fast` | 150ms | 微交互（按钮、图标） |
| `--transition-normal` | 200ms | 标准过渡（卡片、输入框） |
| `--transition-slow` | 300ms | 复杂动画（模态框、页面切换） |

### 9.2 缓动函数

| Token | 值 | 用途 |
|-------|-----|------|
| `--ease-default` | `ease` | 默认过渡 |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | 平滑过渡 |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | 退出动画 |

### 9.3 微交互

#### 按钮悬停

```css
.btn {
  transition: all 150ms ease;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn:active {
  transform: translateY(0);
  transition-duration: 100ms;
}
```

#### 卡片悬停

```css
.card {
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
}
```

#### 输入框聚焦

```css
.input {
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.input:focus {
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
```

### 9.4 加载状态

#### 骨架屏

```css
.skeleton {
  background: linear-gradient(
    90deg,
    rgba(107, 114, 128, 0.1) 25%,
    rgba(107, 114, 128, 0.2) 50%,
    rgba(107, 114, 128, 0.1) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### 旋转加载

```css
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3B82F6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 9.5 状态过渡

#### 淡入

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 200ms ease forwards;
}
```

#### 滑入

```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-in-up {
  animation: slideUp 200ms cubic-bezier(0, 0, 0.2, 1) forwards;
}
```

#### 脉冲

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

### 9.6 减少动画偏好

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 10. 页面布局

### 10.1 上传页 (Upload Page)

```
┌─────────────────────────────────────────────────────────┐
│  Header                                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │           报告审核系统                           │   │
│  │     上传检验报告，系统将自动解析并核对文档内容      │   │
│  │                                                 │   │
│  │  ┌─────────────────────────────────────────┐   │   │
│  │  │                                         │   │   │
│  │  │     [拖拽上传区域]                       │   │   │
│  │  │                                         │   │   │
│  │  │     点击或拖拽文件到此处上传              │   │   │
│  │  │     支持 PDF / DOCX 格式                 │   │   │
│  │  │                                         │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  │                                                 │   │
│  │  ┌──────────┐  ┌──────────┐                    │   │
│  │  │ PDF 文件  │  │ Word 文档 │                    │   │
│  │  │ 推荐格式  │  │ DOCX格式 │                    │   │
│  │  └──────────┘  └──────────┘                    │   │
│  │                                                 │   │
│  │  ┌─────────────────────────────────────────┐   │   │
│  │  │ 核对内容                                 │   │   │
│  │  │ • 首页与第三页关键字段一致性核对          │   │   │
│  │  │ • 样品描述表格字段提取                    │   │   │
│  │  │ • 照片页中文标签 OCR 识别                 │   │   │
│  │  │ • 表格字段与标签内容比对                  │   │   │
│  │  │ • 检验项目逐项核对                        │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Footer                                                 │
└─────────────────────────────────────────────────────────┘
```

### 10.2 结果页 (Result Page)

参考MIT研究的三栏布局，优化信息架构：

```
┌─────────────────────────────────────────────────────────┐
│  Header                                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  [文件信息卡]  [统计概览卡]  [操作按钮组]          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────┐  ┌─────────────────────────────────┐   │
│  │             │  │                                 │   │
│  │  核对内容    │  │        详细核对结果              │   │
│  │  清单        │  │                                 │   │
│  │             │  │  ┌─────────────────────────┐   │   │
│  │  ▼ 报告基础  │  │  │ C01 首页与第三页一致性    │   │   │
│  │    C01 通过  │  │  │                         │   │   │
│  │    C02 通过  │  │  │ 委托方: XXX公司           │   │   │
│  │    C03 警告  │  │  │ 样品名称: XXX产品         │   │   │
│  │    C04 通过  │  │  │ ...                     │   │   │
│  │             │  │  └─────────────────────────┘   │   │
│  │  ▶ 样品照片  │  │                                 │   │
│  │  ▶ 检验项目  │  │  ┌─────────────────────────┐   │   │
│  │  ▶ 页码校验  │  │  │ C03 生产日期格式          │   │   │
│  │             │  │  │                         │   │   │
│  │  ─────────  │  │  │ ⚠ 格式不一致              │   │   │
│  │             │  │  │ 表格: 2024-01-15          │   │   │
│  │  筛选:      │  │  │ 标签: 2024年01月15日       │   │   │
│  │  [全部]     │  │  │                         │   │   │
│  │  [仅错误]   │  │  └─────────────────────────┘   │   │
│  │  [仅警告]   │  │                                 │   │
│  │             │  │                                 │   │
│  └─────────────┘  └─────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  检验项目表格                                      │   │
│  │  ┌──────┬──────────┬────────┬────────┬────────┐ │   │
│  │  │ 序号 │ 检验项目 │ 标准要求│ 检验结果│ 单项结论│ │   │
│  │  ├──────┼──────────┼────────┼────────┼────────┤ │   │
│  │  │  1   │   ...    │   ...  │   ...  │   ✓    │ │   │
│  │  └──────┴──────────┴────────┴────────┴────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Footer                                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 11. 无障碍设计

### 11.1 对比度

- 文字与背景对比度至少 4.5:1
- 大文字（18px+ 或 14px+粗体）对比度至少 3:1
- 交互元素对比度至少 3:1

### 11.2 焦点状态

```css
/* 所有可交互元素必须有可见焦点 */
:focus-visible {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}

/* 自定义焦点样式 */
.btn:focus-visible {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
}
```

### 11.3 键盘导航

- 所有功能可通过键盘访问
- Tab 顺序符合视觉顺序
- 提供跳过链接（Skip Link）

---

## 12. 图标系统

使用 **Lucide React** 或 **@ant-design/icons** 图标库，保持一致性：

| 用途 | 图标名 |
|------|--------|
| 上传 | `Upload` |
| 文件 | `FileText`, `FileSpreadsheet` |
| 成功 | `CheckCircle2` |
| 错误 | `XCircle` |
| 警告 | `AlertTriangle` |
| 信息 | `Info` |
| 搜索 | `Search` |
| 筛选 | `Filter` |
| 导出 | `Download` |
| 刷新 | `RefreshCw` |
| 展开 | `ChevronDown` |
| 折叠 | `ChevronUp` |
| 图片 | `Image` |
| 表格 | `Table` |
| 设置 | `Settings` |

---

## 13. 设计Token汇总

### 13.1 CSS Variables

```css
:root {
  /* Colors - Primary */
  --color-primary: #3B82F6;
  --color-primary-light: #60A5FA;
  --color-primary-dark: #2563EB;
  --color-secondary: #06B6D4;
  --color-accent: #8B5CF6;

  /* Colors - Status */
  --color-success: #10B981;
  --color-success-light: #34D399;
  --color-warning: #F59E0B;
  --color-warning-light: #FBBF24;
  --color-error: #EF4444;
  --color-error-light: #F87171;
  --color-info: #6B7280;

  /* Backgrounds */
  --bg-primary: #0A0E17;
  --bg-secondary: #111827;
  --bg-tertiary: #1F2937;
  --bg-elevated: #1A2332;
  --bg-card: rgba(17, 24, 39, 0.85);
  --bg-input: #0F172A;

  /* Text */
  --text-primary: #F9FAFB;
  --text-secondary: #D1D5DB;
  --text-tertiary: #9CA3AF;
  --text-muted: #6B7280;
  --text-inverse: #1F2937;

  /* Border */
  --border-subtle: rgba(59, 130, 246, 0.1);
  --border-default: rgba(59, 130, 246, 0.2);
  --border-strong: rgba(59, 130, 246, 0.3);
  --border-focus: #3B82F6;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
  --shadow-glow-sm: 0 0 10px rgba(59, 130, 246, 0.2);
  --shadow-glow-md: 0 0 20px rgba(59, 130, 246, 0.3);
  --shadow-glow-success: 0 0 10px rgba(16, 185, 129, 0.3);
  --shadow-glow-error: 0 0 10px rgba(239, 68, 68, 0.3);

  /* Typography */
  --font-sans: Inter, -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', Consolas, monospace;

  /* Font Sizes */
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 30px;

  /* Animation */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;
  --transition-slow: 300ms ease;

  /* Z-Index */
  --z-base: 0;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-modal: 300;
  --z-tooltip: 400;
}
```

---

## 14. 实施建议

### 14.1 优先级

1. **P0 - 基础样式**: 色彩、字体、间距系统
2. **P1 - 核心组件**: 按钮、卡片、输入框
3. **P2 - 复合组件**: 表格、上传区域、核对面板
4. **P3 - 页面重构**: 上传页、结果页

### 14.2 技术实现

- 使用 CSS Modules 或 Tailwind CSS
- 保持与 Ant Design 的兼容性
- 逐步替换现有样式，避免一次性大改
- 添加设计Token到 CSS Variables
- 使用现有的 `OptimizedCard` 和 `OptimizedBackground` 组件

### 14.3 与现有组件的整合

以下现有组件与规范兼容：
- ✅ `OptimizedCard` - 直接使用
- ✅ `OptimizedBackground` - 直接使用
- ✅ `design-system.css` - 大部分样式可直接使用

需要调整的组件：
- ⚠️ `GlowCard` - 建议迁移到 `OptimizedCard`
- ⚠️ `ParticleBackground` - 建议迁移到 `OptimizedBackground`

### 14.4 验收标准

- [ ] 所有颜色符合 WCAG 2.1 AA 标准
- [ ] 所有交互元素有可见焦点状态
- [ ] 动画支持 `prefers-reduced-motion`
- [ ] 组件在 375px - 1440px 范围内正常显示
- [ ] 深色主题一致性
- [ ] 表格文字不小于14px，行高至少1.5倍

---

## 附录

### A. 参考资源

- [Inter Font](https://rsms.me/inter/)
- [Lucide Icons](https://lucide.dev/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Ant Design Dark Theme](https://ant.design/docs/spec/dark)
- [调研报告](./ui-research-report.md)

### B. 变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-13 | 初始版本 |
| v2.0 | 2026-02-13 | 基于调研报告更新色彩系统 |
| v2.1 | 2026-02-13 | 与现有组件对齐，添加实施建议 |

### C. 调研报告关键建议摘要

1. **避免纯黑色**: 使用 `#0f172a` (slate-900) 作为主背景
2. **柔和白色文字**: 使用 `#f9fafb` 而非纯白
3. **降低饱和度**: 使用柔和的强调色，避免"振动"效果
4. **专业医疗感**: 移除过度霓虹效果，使用克制的配色
5. **数据可读性**: 表格文字不小于14px，行高至少1.5倍
6. **状态清晰**: 不仅依赖颜色，同时使用图标和文字标签
7. **三栏布局**: 参考MIT研究的信息架构
