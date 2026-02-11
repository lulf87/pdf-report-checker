# LLM集成配置指南

## 概述

本项目支持使用Claude (Anthropic) 或OpenAI API来增强PDF解析和OCR处理能力。

## 快速开始

### 1. 安装依赖

```bash
cd python_backend
pip install anthropic openai python-dotenv
```

### 2. 获取API密钥

#### Claude API (推荐)
1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 在API Keys页面创建新的API密钥
4. 复制API密钥

#### OpenAI API (备选)
1. 访问 https://platform.openai.com/api-keys
2. 注册/登录账号
3. 创建新的API密钥
4. 复制API密钥

### 3. 配置环境变量

#### 方式一：创建.env文件（推荐）

```bash
# 复制示例配置
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# 使用Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 或使用OpenAI API
OPENAI_API_KEY=sk-xxxxx

# 启用LLM功能
ENABLE_LLM_POST_PROCESSING=true
```

#### 方式二：系统环境变量

```bash
# macOS/Linux
export ANTHROPIC_API_KEY=sk-ant-xxxxx
export ENABLE_LLM_POST_PROCESSING=true

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-xxxxx"
$env:ENABLE_LLM_POST_PROCESSING="true"
```

### 4. 验证配置

运行测试脚本验证LLM配置：

```bash
python test_llm_config.py
```

## 功能说明

### LLM服务提供的功能

1. **表格重建** (`reconstruct_table`)
   - 从OCR文本重建表格结构
   - 检测跨页表格延续
   - 处理复杂表格布局

2. **OCR纠错** (`correct_ocr`)
   - 修正OCR识别错误
   - 提高字段提取准确率

3. **结构化字段提取** (`extract_structured_fields`)
   - 从标签文本中提取结构化数据
   - 支持批号、序列号、生产日期等字段

### 使用示例

```python
from services.llm_service import get_llm_service

# 获取LLM服务实例
llm = get_llm_service()

# 检查服务是否可用
if llm.is_available():
    # 表格重建
    result = llm.reconstruct_table(
        ocr_text=ocr_text,
        page_context={"page_num": 4, "prev_table_rows": 15}
    )

    # OCR纠错
    corrected = llm.correct_ocr(
        text=raw_ocr_text,
        expected_fields=["批号", "序列号", "生产日期"]
    )

    # 结构化字段提取
    fields = llm.extract_structured_fields(
        label_text=label_ocr_text,
        expected_fields=["batch_number", "serial_number", "production_date"]
    )
```

## API配置选项

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API密钥 | 无 |
| `OPENAI_API_KEY` | OpenAI API密钥 | 无 |
| `LLM_MODEL` | 使用的模型 | claude-3-5-sonnet-20241022 |
| `LLM_MAX_TOKENS` | 最大token数 | 4096 |
| `LLM_TEMPERATURE` | 温度参数 | 0 |
| `ENABLE_LLM_POST_PROCESSING` | 启用LLM后处理 | false |

### 成本估算

| 提供商 | 模型 | 输入成本 | 输出成本 |
|--------|------|----------|----------|
| Claude | claude-3-5-sonnet | $3/MTok | $15/MTok |
| Claude | claude-3-haiku | $0.25/MTok | $1.25/MTok |
| OpenAI | gpt-4o-mini | $0.15/MTok | $0.60/MTok |

典型处理成本：约$0.0025-0.005/报告

## 常见问题

### Q: LLM服务无法启动？
A: 检查以下几点：
1. API密钥是否正确配置
2. 是否安装了所需的依赖包
3. 网络连接是否正常
4. 运行 `python test_llm_config.py` 诊断

### Q: 如何禁用LLM功能？
A: 在.env文件中设置：
```
ENABLE_LLM_POST_PROCESSING=false
```

### Q: 可以同时使用多个LLM提供商吗？
A: 当前版本按优先级使用：Claude > OpenAI。如需同时使用，请修改 `llm_service.py`

### Q: API调用失败会怎样？
A: 系统会自动降级到基础OCR处理，不会中断正常流程

## 开发说明

### 添加新的LLM功能

在 `services/llm_service.py` 中添加新方法：

```python
def your_new_function(self, input_data):
    if not self.is_available():
        return self._fallback_method(input_data)

    prompt = f"""
    你的提示词...
    {input_data}
    """

    try:
        if self.provider == "anthropic":
            response = self.client.messages.create(...)
            return self._parse_result(response)
        elif self.provider == "openai":
            response = self.client.chat.completions.create(...)
            return self._parse_result(response)
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return self._fallback_method(input_data)
```

### 集成到报告核对流程

在 `services/report_checker.py` 中调用LLM服务：

```python
from services.llm_service import get_llm_service

class ReportChecker:
    def __init__(self):
        # ...
        self.llm_service = get_llm_service()

    def _extract_sample_table(self, pdf_path: str, pages: List[Any]):
        # 现有逻辑...

        # 如果启用了LLM，可以进行后处理
        if self.llm_service.is_available():
            # 使用LLM优化表格提取结果
            pass
```

## 安全建议

1. **不要将API密钥提交到版本控制系统**
   - .env文件已在.gitignore中
   - 只提交.env.example作为示例

2. **设置使用限额**
   - 在Anthropic/OpenAI控制台设置使用限额
   - 避免意外产生高额费用

3. **监控API使用量**
   - 定期检查API使用情况
   - 实施请求缓存以减少重复调用

## 更新日志

- **2026-02-11**: 初始版本，支持Claude和OpenAI API
