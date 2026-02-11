"""
LLM服务 - 用于PDF解析后处理
支持OpenRouter、Claude (Anthropic) 和OpenAI API
"""
import os
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import settings, is_llm_enabled, get_llm_provider


class LLMService:
    """LLM服务基类"""

    def __init__(self):
        self.provider = get_llm_provider()
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化API客户端"""
        if self.provider == "openrouter" and settings.OPENROUTER_API_KEY:
            try:
                import openai
                # OpenRouter使用OpenAI兼容API
                self.client = openai.OpenAI(
                    base_url=settings.OPENROUTER_BASE_URL,
                    api_key=settings.OPENROUTER_API_KEY
                )
                print(f"✓ OpenRouter客户端初始化成功，模型: {settings.LLM_MODEL}")
            except ImportError:
                print("警告: 未安装openai包，请运行: pip install openai")
                self.provider = "none"

        elif self.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                print(f"✓ Anthropic客户端初始化成功，模型: {settings.LLM_MODEL}")
            except ImportError:
                print("警告: 未安装anthropic包，请运行: pip install anthropic")
                self.provider = "none"

        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                print(f"✓ OpenAI客户端初始化成功，模型: {settings.LLM_MODEL}")
            except ImportError:
                print("警告: 未安装openai包，请运行: pip install openai")
                self.provider = "none"

    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self.provider != "none" and self.client is not None

    def reconstruct_table(
        self,
        ocr_text: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从OCR文本重建表格结构

        Args:
            ocr_text: OCR提取的文本
            page_context: 页面上下信息 (page_num, prev_table_rows, etc.)

        Returns:
            包含headers, rows, is_continuation, confidence的字典
        """
        if not self.is_available():
            return self._fallback_reconstruction(ocr_text, page_context)

        prompt = self._build_table_reconstruction_prompt(ocr_text, page_context)

        try:
            if self.provider == "openrouter":
                return self._openrouter_reconstruct(prompt)
            elif self.provider == "anthropic":
                return self._anthropic_reconstruct(prompt)
            elif self.provider == "openai":
                return self._openai_reconstruct(prompt)
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._fallback_reconstruction(ocr_text, page_context)

    def correct_ocr(
        self,
        text: str,
        expected_fields: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        纠正OCR文本错误

        Args:
            text: 原始OCR文本
            expected_fields: 期望的字段列表（用于提示）
            context: 额外上下文信息

        Returns:
            纠正后的文本
        """
        if not self.is_available():
            return text

        prompt = self._build_ocr_correction_prompt(text, expected_fields, context)

        try:
            if self.provider == "openrouter":
                return self._openrouter_chat(prompt)
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=settings.LLM_MODEL,
                    max_tokens=2000,
                    temperature=settings.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=2000
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"OCR纠正失败: {e}")
            return text

    def extract_structured_fields(
        self,
        label_text: str,
        expected_fields: List[str]
    ) -> Dict[str, Any]:
        """
        从标签文本中提取结构化字段

        Args:
            label_text: 标签OCR文本
            expected_fields: 期望提取的字段名列表

        Returns:
            结构化字段字典
        """
        if not self.is_available():
            return self._fallback_field_extraction(label_text, expected_fields)

        prompt = f"""
从以下产品标签文本中提取结构化字段。

期望字段: {', '.join(expected_fields)}

标签文本:
{label_text}

请以JSON格式返回，包含所有找到的字段及其值。如果某个字段未找到，值设为空字符串。
返回格式示例:
{{
    "batch_number": {{"value": "ABC123", "confidence": 0.95}},
    "serial_number": {{"value": "SN456", "confidence": 0.98}},
    ...
}}

只返回JSON，不要其他解释。
"""

        try:
            result_text = ""
            if self.provider == "openrouter":
                result_text = self._openrouter_chat(prompt, json_mode=True)
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=settings.LLM_MODEL,
                    max_tokens=2000,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                result_text = response.choices[0].message.content

            # 解析JSON结果
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = re.sub(r'^```(?:json)?\n', '', result_text)
                result_text = re.sub(r'\n```$', '', result_text)

            return json.loads(result_text)

        except Exception as e:
            print(f"结构化字段提取失败: {e}")
            return self._fallback_field_extraction(label_text, expected_fields)

    def _openrouter_chat(self, prompt: str, json_mode: bool = False) -> str:
        """OpenRouter聊天接口"""
        kwargs = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }

        # 某些模型支持JSON模式
        if json_mode and "gemini" not in settings.LLM_MODEL.lower():
            # Gemini不支持response_format参数
            try:
                kwargs["response_format"] = {"type": "json_object"}
            except:
                pass

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()

    def _openrouter_reconstruct(self, prompt: str) -> Dict[str, Any]:
        """使用OpenRouter API重建表格"""
        result_text = self._openrouter_chat(prompt)

        # 解析JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)

        return json.loads(result_text)

    def _build_table_reconstruction_prompt(
        self,
        ocr_text: str,
        page_context: Dict[str, Any]
    ) -> str:
        """构建表格重建提示词"""
        prev_rows = page_context.get('prev_table_rows', 'unknown')

        prompt = f"""
你是表格结构重建专家。请从以下OCR文本中重建表格结构。

**页面信息:**
- 页码: {page_context.get('page_num', 'N/A')}
- 上一页表格行数: {prev_rows}

**OCR文本:**
{ocr_text}

**任务:**
1. 识别表格的列结构（headers）
2. 提取所有数据行
3. 判断此页是否延续上一页的表格

**返回格式（JSON）:**
{{
    "headers": ["序号", "部件名称", "规格型号", "序列号/批号", "生产日期", "备注"],
    "rows": [
        ["16", "光纤（15m）（可选）", "S100002", "/", "/", "/"],
        ["17", "光纤（30m）（可选）", "H700180", "/", "/", "本次检测未使用"]
    ],
    "is_continuation": true,
    "confidence": 0.95
}}

**注意事项:**
- 如果第一行包含"序号"或"部件名称"等表头特征，则是新表
- 如果第一行是数字序号（如16），则可能是延续
- 列数应与样品描述表格一致（通常6列）
- 只返回JSON，不要其他解释
"""

        return prompt

    def _build_ocr_correction_prompt(
        self,
        text: str,
        expected_fields: Optional[List[str]],
        context: Optional[str]
    ) -> str:
        """构建OCR纠正提示词"""
        prompt = f"""
请纠正以下OCR文本中的错误。

**原始文本:**
{text}
"""

        if expected_fields:
            prompt += f"\n**期望字段:** {', '.join(expected_fields)}"

        if context:
            prompt += f"\n**上下文:** {context}"

        prompt += """

**要求:**
1. 修正明显的OCR错误（如0/O混淆）
2. 保持原有格式和结构
3. 只返回纠正后的文本，不要解释
"""

        return prompt

    def _anthropic_reconstruct(self, prompt: str) -> Dict[str, Any]:
        """使用Claude API重建表格"""
        response = self.client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text

        # 解析JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)

        return json.loads(result_text)

    def _openai_reconstruct(self, prompt: str) -> Dict[str, Any]:
        """使用OpenAI API重建表格"""
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content

        # 解析JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)

        return json.loads(result_text)

    def _fallback_reconstruction(
        self,
        ocr_text: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """降级处理：不使用LLM时返回基础解析"""
        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]

        # 尝试识别表格结构
        if len(lines) > 0:
            # 假设第一行可能是表头
            headers = [lines[0]] if '部件' in lines[0] or '序号' in lines[0] else []
            rows = lines[1:] if headers else lines

            return {
                "headers": headers,
                "rows": [[cell] for cell in rows],
                "is_continuation": False,
                "confidence": 0.5,
                "method": "fallback"
            }

        return {
            "headers": [],
            "rows": [],
            "is_continuation": False,
            "confidence": 0.0,
            "method": "fallback"
        }

    def _fallback_field_extraction(
        self,
        label_text: str,
        expected_fields: List[str]
    ) -> Dict[str, Any]:
        """降级处理：基础字段提取"""
        result = {}
        for field in expected_fields:
            result[field] = {"value": "", "confidence": 0.0}
        return result


# 全局单例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取LLM服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
