# 报告审核工具

基于 Electron + Python 的桌面应用，用于检验报告的自动化核对。

## 功能特性

- 📄 支持 PDF 和 DOCX 文件上传
- 🔍 自动解析文档结构和表格
- 📝 OCR 识别中文标签内容
- ✅ 字段一致性核对
- 📊 可视化结果展示
- 🖼️ 照片覆盖性检查

## 技术栈

### 前端

- Electron 28
- React 18
- Ant Design 5
- Vite

### 后端

- Python 3.9+
- FastAPI
- PaddleOCR
- PyMuPDF

## 项目结构

```
report-checker/
├── package.json              # 主项目配置
├── src/
│   ├── main/                 # Electron 主进程
│   │   ├── main.js          # 主入口
│   │   └── preload.js       # 预加载脚本
│   └── renderer/            # 前端 React 应用
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.jsx
│           ├── main.jsx
│           └── components/
├── python_backend/          # Python 后端服务
│   ├── main.py             # FastAPI 入口
│   ├── requirements.txt
│   ├── models/             # 数据模型
│   │   └── schemas.py
│   └── services/           # 业务服务
│       ├── pdf_parser.py
│       ├── docx_parser.py
│       ├── ocr_service.py
│       └── report_checker.py
└── uploads/                # 上传文件存储
```

## 快速开始

### 1. 安装依赖

```bash
# 安装所有依赖（前端 + 后端）
1
```

或者分别安装：

```bash
# 主项目和 Electron
npm install

# 前端 React
cd src/renderer && npm install

# Python 后端
cd python_backend
pip install -r requirements.txt
```

### 2. 开发模式运行

```bash
# 同时启动 Electron 和 Python 后端
npm run dev
```

这会启动：

- Python 后端服务: http://127.0.0.1:8000
- Electron 前端: http://localhost:5173

### 3. 生产构建

```bash
# 构建前端和后端
npm run build
```

## 开发说明

### 后端 API

| 端点                                   | 方法 | 说明        |
| -------------------------------------- | ---- | ----------- |
| `/health`                            | GET  | 健康检查    |
| `/api/upload`                        | POST | 上传文件    |
| `/api/parse/{file_id}`               | POST | 解析文件    |
| `/api/ocr/{file_id}/page/{page_num}` | POST | OCR识别页面 |
| `/api/check/{file_id}`               | POST | 执行核对    |
| `/api/result/{file_id}`              | GET  | 获取结果    |
| `/api/export/{file_id}`              | GET  | 导出报告    |

### 新功能

#### 详细比对信息

启用详细比对模式可以查看每个部件的完整比对过程：

```bash
POST /api/check/{file_id}?enable_detailed=true
```

返回结果包含：
- `comparison_details`: 每个比对步骤的详细记录
- `matched_photos`: 匹配到的照片列表
- `matched_labels`: 匹配到的标签列表
- `match_reason`: 匹配/不匹配的原因

#### 报告导出

支持导出PDF和Excel格式的核对报告：

**界面导出：**
- 核对完成后，点击"导出报告"按钮
- 支持 PDF 报告（适合打印和分享）
- 支持 Excel 表格（适合数据分析）

**API导出：**
```bash
# 导出PDF
GET /api/export/{file_id}?format=pdf

# 导出Excel
GET /api/export/{file_id}?format=excel

# 导出JSON
GET /api/export/{file_id}?format=json
```

**PDF报告内容：**
- 文件信息和核对时间
- 核对统计（总部件数、通过/失败/警告数）
- 首页与第三页字段比对
- 每个部件的详细核对结果
- 问题汇总

**Excel报告内容：**
- Sheet1: 核对概览
- Sheet2: 部件核对明细
- Sheet3: 问题汇总

#### LLM增强比对

启用大模型(LLM)辅助比对，在OCR识别失败时自动调用LLM：

**方式1：界面开关**
- 在文件上传后的准备页面，有一个"LLM 增强识别"开关
- 开启后，本次核对将使用LLM辅助识别

**方式2：API参数**
```bash
POST /api/check/{file_id}?enable_llm=true
```

**环境变量配置：**
```bash
ENABLE_LLM_COMPARISON=true
LLM_COMPARISON_MODE=fallback  # fallback/enhance/disabled
```

### 核对流程

1. **文件上传** - 接收 PDF/DOCX 文件
2. **文档解析** - 提取页面、表格、图片
3. **字段提取** - 识别首页和第三页关键字段
4. **OCR识别** - 识别中文标签内容
5. **字段比对** - 比对表格与标签字段
6. **结果生成** - 生成核对报告

## 许可证

MIT
