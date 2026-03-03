# Report Checker Pro

检验报告综合核对工具 - 用于医疗器械检验报告的自动化核对。

## 功能特性

### 模块一：PTR 条款核对
- 核对检验报告与产品技术要求（PTR）之间的条款文本一致性
- 支持条款层级解析（2 → 2.1 → 2.1.1 → ...）
- 自动识别"见表X"引用并展开表格内容比对
- 差异高亮显示，支持筛选（全部/仅不一致）

### 模块二：报告自身核对
- **C01-C03**: 首页/第三页字段一致性核对
- **C04**: 样品描述表格核对
- **C05**: 照片覆盖性核对
- **C06**: 中文标签覆盖核对
- **C07**: 检验项目单项结论逻辑核对
- **C08**: 非空字段核对
- **C09**: 序号连续性核对
- **C10**: 续表标记核对
- **C11**: 页码连续性核对

### 通用特性
- 🎨 玻璃拟态 UI 设计，深色主题
- 🔄 流畅的弹簧物理动画效果
- 📄 PDF 报告导出
- 🔍 OCR 自动识别（PaddleOCR）
- 🤖 LLM 增强识别（可选，支持 GPT-4o/Gemini）

## 技术栈

**后端**:
- Python 3.12+
- FastAPI
- PyMuPDF (PDF 解析)
- PaddleOCR (扫描件识别)
- ReportLab (PDF 导出)

**前端**:
- React 19
- TypeScript
- Vite 7
- TailwindCSS v4
- Framer Motion

## 项目结构

```
report-checker-pro/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   └── models/         # 数据模型
│   ├── tests/              # 测试文件
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── components/     # UI 组件
│   │   └── services/       # API 调用
│   └── package.json        # Node 依赖
├── start.sh                # 一键启动脚本
└── README.md               # 本文件
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- npm 或 pnpm

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd report-checker-pro
```

2. **安装后端依赖**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd ../frontend
npm install
```

4. **配置环境变量（可选）**

创建 `backend/.env` 文件以启用 LLM 增强功能：
```env
OPENROUTER_API_KEY=your-api-key
LLM_MODEL=google/gemini-2.0-flash-exp
ENABLE_LLM_COMPARISON=true
LLM_COMPARISON_MODE=fallback
```

### 启动服务

**方式一：使用启动脚本（推荐）**
```bash
./start.sh start
```

**方式二：手动启动**

后端：
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

前端：
```bash
cd frontend
npm run dev
```

### 访问应用

- 前端界面: http://127.0.0.1:5173
- 后端 API: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs

## 使用说明

### PTR 条款核对

1. 在 Dashboard 点击 "PTR 条款核对"
2. 上传检验报告 PDF 和产品技术要求 PDF
3. 点击 "开始核对"
4. 查看核对结果，可筛选查看全部或仅不一致条款
5. 点击 "导出 PDF" 下载核对报告

### 报告自身核对

1. 在 Dashboard 点击 "报告自身核对"
2. 上传检验报告 PDF
3. （可选）启用 LLM 增强识别
4. 点击 "开始核对"
5. 查看 C01-C11 各项核对结果
6. 点击 "导出 PDF" 下载核对报告

## 开发命令

### 后端测试
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### 前端构建
```bash
cd frontend
npm run build
```

### 停止服务
```bash
./start.sh stop
```

### 查看状态
```bash
./start.sh status
```

## 日志位置

- 后端日志: `logs/backend.log`
- 前端日志: `logs/frontend.log`

## License

MIT
