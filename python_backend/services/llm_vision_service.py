"""
视觉大模型OCR服务
基于Gemini 2.0 Flash或Claude 3.5 Sonnet的视觉能力进行OCR识别
能够识别符号形式的信息（如▲、■等）和复杂布局的标签
"""
import os
import json
import re
import base64
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import io

from config import settings, get_llm_provider


class LLMVisionService:
    """视觉大模型OCR服务"""

    # 字段提取提示词
    VISION_OCR_PROMPT = """你是一个专业的医疗器械标签OCR识别专家。请仔细分析这张产品标签照片，提取以下信息：

**需要识别的字段：**
1. 产品名称 (product_name) - 标签上的产品名称
2. 型号规格 (model) - 产品型号，可能标记为"型号"、"规格"或"REF"
3. 批号 (batch_number) - 可能标记为"批号"、"LOT"、"Batch"或条形码标识符(10)
4. 序列号 (serial_number) - 可能标记为"序列号"、"SN"、"S/N"或条形码标识符(21)
5. 生产日期 (production_date) - 可能标记为"生产日期"、"MFG"、"MFD"或条形码标识符(11)
6. 失效日期 (expiration_date) - 可能标记为"失效日期"、"有效期至"、"EXP"或条形码标识符(17)

**重要提示：**
- 注意标签上可能使用符号来指示字段，如：
  - ▲ 或 ■ 可能表示生产日期
  - ● 或 ◆ 可能表示失效日期
  - 其他几何符号也可能用于标记不同字段
- 条形码中的数据标识符格式：(11)后跟6位数字表示生产日期YYMMDD，(17)后跟6位数字表示失效日期YYMMDD，(10)后跟批号，(21)后跟序列号
- 型号可能以"REF"字样指示
- 日期格式可能是YYYY-MM-DD、YYYY/MM/DD或YYMMDD
- **特别注意表格中的型号**：如果图像包含表格，注意查找"显示触控一体机"、"脉冲电场消融设备"等产品名称对应的型号，型号通常是类似"ENGX-AWG-PC01"、"ENGX-LCG-50"的格式（大写字母+连字符+数字/字母组合）
- **型号格式提示**：常见型号格式包括 ENGX-XXX-XXX、XXXX-XXX-XXX 等，由大写字母、数字和连字符组成

**请以下面JSON格式返回识别结果：**
{
    "product_name": {"value": "产品名称", "confidence": 0.95},
    "model": {"value": "型号", "confidence": 0.95},
    "batch_number": {"value": "批号", "confidence": 0.95},
    "serial_number": {"value": "序列号", "confidence": 0.95},
    "production_date": {"value": "生产日期", "confidence": 0.95},
    "expiration_date": {"value": "失效日期", "confidence": 0.95},
    "full_text": "标签的完整文本内容"
}

**注意事项：**
- 如果某个字段在标签上不存在，value设为空字符串
- confidence表示你对识别结果的置信度（0-1之间）
- full_text包含你识别到的所有文本内容
- 只返回JSON，不要其他解释"""

    def __init__(self):
        self.provider = get_llm_provider()
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化API客户端"""
        if self.provider == "openrouter" and settings.OPENROUTER_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(
                    base_url=settings.OPENROUTER_BASE_URL,
                    api_key=settings.OPENROUTER_API_KEY
                )
                print(f"✓ OpenRouter视觉客户端初始化成功")
            except ImportError:
                print("警告: 未安装openai包")
                self.provider = "none"

        elif self.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                print(f"✓ Anthropic视觉客户端初始化成功")
            except ImportError:
                print("警告: 未安装anthropic包")
                self.provider = "none"

        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                print(f"✓ OpenAI视觉客户端初始化成功")
            except ImportError:
                print("警告: 未安装openai包")
                self.provider = "none"

    def is_available(self) -> bool:
        """检查视觉LLM服务是否可用"""
        return self.provider != "none" and self.client is not None

    def _encode_image(self, image_path: str) -> Tuple[str, str]:
        """
        将图片编码为base64
        返回: (base64字符串, mime类型)
        """
        with open(image_path, "rb") as f:
            image_data = f.read()

        # 检测文件类型
        mime_type = "image/jpeg"
        if image_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            mime_type = "image/jpeg"
        elif image_path.lower().endswith('.webp'):
            mime_type = "image/webp"

        base64_data = base64.b64encode(image_data).decode('utf-8')
        return base64_data, mime_type

    def _encode_image_array(self, img_array: Any) -> Tuple[str, str]:
        """
        将numpy数组编码为base64
        返回: (base64字符串, mime类型)
        """
        import cv2

        # 编码为JPEG
        _, buffer = cv2.imencode('.jpg', img_array)
        base64_data = base64.b64encode(buffer).decode('utf-8')
        return base64_data, "image/jpeg"

    def recognize_image(self, image_path: str) -> Dict[str, Any]:
        """
        对图片进行视觉OCR识别

        Args:
            image_path: 图片路径

        Returns:
            包含识别结果的字典
        """
        if not self.is_available():
            raise RuntimeError("视觉LLM服务不可用，请检查API密钥配置")

        base64_image, mime_type = self._encode_image(image_path)

        try:
            if self.provider == "openrouter":
                return self._openrouter_recognize(base64_image, mime_type)
            elif self.provider == "anthropic":
                return self._anthropic_recognize(base64_image, mime_type)
            elif self.provider == "openai":
                return self._openai_recognize(base64_image, mime_type)
            else:
                raise RuntimeError(f"不支持的提供商: {self.provider}")
        except Exception as e:
            print(f"视觉OCR识别失败: {e}")
            raise

    def recognize_image_array(self, img_array: Any) -> Dict[str, Any]:
        """
        对图片数组进行视觉OCR识别

        Args:
            img_array: numpy图片数组

        Returns:
            包含识别结果的字典
        """
        if not self.is_available():
            raise RuntimeError("视觉LLM服务不可用，请检查API密钥配置")

        base64_image, mime_type = self._encode_image_array(img_array)

        try:
            if self.provider == "openrouter":
                return self._openrouter_recognize(base64_image, mime_type)
            elif self.provider == "anthropic":
                return self._anthropic_recognize(base64_image, mime_type)
            elif self.provider == "openai":
                return self._openai_recognize(base64_image, mime_type)
            else:
                raise RuntimeError(f"不支持的提供商: {self.provider}")
        except Exception as e:
            print(f"视觉OCR识别失败: {e}")
            raise

    def _openrouter_recognize(self, base64_image: str, mime_type: str) -> Dict[str, Any]:
        """使用OpenRouter API进行视觉识别"""
        model = settings.LLM_MODEL

        # 构建消息内容
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.VISION_OCR_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

        result_text = response.choices[0].message.content.strip()
        return self._parse_result(result_text)

    def _anthropic_recognize(self, base64_image: str, mime_type: str) -> Dict[str, Any]:
        """使用Anthropic Claude API进行视觉识别"""
        model = settings.LLM_MODEL
        if not model.startswith("claude"):
            model = "claude-3-5-sonnet-20241022"  # 默认使用Claude 3.5 Sonnet

        # 提取媒体类型
        media_type = mime_type

        response = self.client.messages.create(
            model=model,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": self.VISION_OCR_PROMPT
                        }
                    ]
                }
            ]
        )

        result_text = response.content[0].text.strip()
        return self._parse_result(result_text)

    def _openai_recognize(self, base64_image: str, mime_type: str) -> Dict[str, Any]:
        """使用OpenAI API进行视觉识别"""
        model = settings.LLM_MODEL
        if not model.startswith("gpt-4"):
            model = "gpt-4o"  # 默认使用GPT-4o

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.VISION_OCR_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

        result_text = response.choices[0].message.content.strip()
        return self._parse_result(result_text)

    def _parse_result(self, result_text: str) -> Dict[str, Any]:
        """解析LLM返回的结果"""
        # 清理markdown代码块
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试提取关键信息
            print(f"JSON解析失败，尝试提取信息: {result_text[:200]}...")
            result = self._extract_info_from_text(result_text)

        # 标准化结果格式
        return self._normalize_result(result)

    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """从非JSON文本中提取信息"""
        result = {
            "product_name": {"value": "", "confidence": 0},
            "model": {"value": "", "confidence": 0},
            "batch_number": {"value": "", "confidence": 0},
            "serial_number": {"value": "", "confidence": 0},
            "production_date": {"value": "", "confidence": 0},
            "expiration_date": {"value": "", "confidence": 0},
            "full_text": text
        }

        # 尝试使用正则提取各个字段
        patterns = {
            "product_name": r'(?:产品名称|Product Name)[：:\s]*([^\n]+)',
            "model": r'(?:型号|规格|Model|REF)[：:\s]*([^\n]+)',
            "batch_number": r'(?:批号|Batch|LOT)[：:\s]*([^\n]+)',
            "serial_number": r'(?:序列号|Serial|SN)[：:\s]*([^\n]+)',
            "production_date": r'(?:生产日期|Production|MFG)[：:\s]*([^\n]+)',
            "expiration_date": r'(?:失效日期|有效期至|Expiration|EXP)[：:\s]*([^\n]+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = {"value": match.group(1).strip(), "confidence": 0.7}

        return result

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化识别结果"""
        normalized = {
            "product_name": {"value": "", "confidence": 0},
            "model": {"value": "", "confidence": 0},
            "batch_number": {"value": "", "confidence": 0},
            "serial_number": {"value": "", "confidence": 0},
            "production_date": {"value": "", "confidence": 0},
            "expiration_date": {"value": "", "confidence": 0},
            "full_text": ""
        }

        # 字段名映射（处理可能的变体）
        field_mappings = {
            "product_name": ["product_name", "productName", "product name", "名称", "产品名称"],
            "model": ["model", "型号", "规格型号", "规格", "型号规格", "REF"],
            "batch_number": ["batch_number", "batchNumber", "batch", "批号", "lot", "lot_number"],
            "serial_number": ["serial_number", "serialNumber", "serial", "序列号", "sn", "s/n"],
            "production_date": ["production_date", "productionDate", "mfg_date", "生产日期", "mfg", "manufacture_date"],
            "expiration_date": ["expiration_date", "expirationDate", "exp_date", "失效日期", "有效期至", "exp", "expiry_date"],
            "full_text": ["full_text", "fullText", "text", "full text", "ocr_text", "raw_text"]
        }

        for standard_field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in result:
                    value = result[name]
                    if isinstance(value, dict):
                        normalized[standard_field] = {
                            "value": str(value.get("value", "")).strip(),
                            "confidence": float(value.get("confidence", 0))
                        }
                    elif isinstance(value, str):
                        normalized[standard_field] = {
                            "value": value.strip(),
                            "confidence": 0.9
                        }
                    break

        # 处理日期格式
        for date_field in ["production_date", "expiration_date"]:
            if normalized[date_field]["value"]:
                normalized[date_field]["value"] = self._normalize_date(
                    normalized[date_field]["value"]
                )

        return normalized

    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式"""
        if not date_str:
            return date_str

        # 移除多余空格
        date_str = date_str.strip()

        # 处理YYMMDD格式（6位数字）
        if re.match(r'^\d{6}$', date_str):
            year = int(date_str[0:2])
            month = date_str[2:4]
            day = date_str[4:6]

            # 判断世纪
            full_year = 2000 + year if year < 50 else 1900 + year
            return f"{full_year}-{month}-{day}"

        # 处理YYYY年MM月DD日格式
        date_str = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日?', r'\1-\2-\3', date_str)

        # 统一分隔符为-
        date_str = date_str.replace('/', '-').replace('.', '-')

        # 确保月份和日期是两位数
        parts = date_str.split('-')
        if len(parts) == 3:
            year = parts[0]
            month = parts[1].zfill(2)
            day = parts[2].zfill(2)
            return f"{year}-{month}-{day}"

        return date_str


# 全局单例
_vision_service: Optional[LLMVisionService] = None


def get_vision_service() -> LLMVisionService:
    """获取视觉LLM服务单例"""
    global _vision_service
    if _vision_service is None:
        _vision_service = LLMVisionService()
    return _vision_service


def is_vision_llm_available() -> bool:
    """检查视觉LLM是否可用"""
    try:
        service = get_vision_service()
        return service.is_available()
    except Exception:
        return False
