"""
VLM (Vision Language Model) service for OCR correction on label images.
"""

import json
import logging
import re
from base64 import b64encode
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _non_empty_string(value: Any) -> str:
    """Return stripped string if value is a non-empty string; otherwise empty."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return ""


class VLMServiceConfig:
    """Configuration for VLM service."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "google/gemini-2.0-flash-exp",
        api_key: str = "",
        base_url: str = "",
        timeout: int = 60,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

        if base_url:
            self.base_url = base_url
        elif provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1"
        elif provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        elif provider == "deepseek":
            self.base_url = "https://api.deepseek.com/v1"
        else:
            self.base_url = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)


class VLMService:
    """VLM service for image-based OCR correction/extraction."""

    def __init__(self, config: VLMServiceConfig | None = None):
        if config is None:
            config = VLMServiceConfig(
                model=settings.llm_model,
                api_key=_non_empty_string(settings.openrouter_api_key),
            )
        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    def _encode_image(self, image_path: str | Path) -> str:
        image_path = Path(image_path)
        with image_path.open("rb") as f:
            return b64encode(f.read()).decode("utf-8")

    def _parse_json_content(self, content: str) -> dict[str, Any]:
        """Parse model text into JSON, tolerating code fences."""
        text = (content or "").strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fenced = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        fenced = re.sub(r"\s*```$", "", fenced)
        try:
            parsed = json.loads(fenced)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        candidates = re.findall(r"\{[\s\S]*\}", text)
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
        return {}

    async def extract_text_from_image(
        self,
        image_path: str | Path,
        prompt: str = "Extract all text from this image. Preserve formatting and structure.",
        expect_json: bool = False,
    ) -> dict[str, Any]:
        if not self.config.is_configured:
            return {"text": "", "error": "VLM not configured"}

        base64_image = self._encode_image(image_path)
        image_path = Path(image_path)

        mime_type = "image/png"
        if image_path.suffix.lower() in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"

        if self.config.provider == "openrouter":
            return await self._extract_via_openrouter(
                base64_image, mime_type, prompt, expect_json
            )
        return await self._extract_via_direct(
            base64_image, mime_type, prompt, expect_json
        )

    async def _extract_via_openrouter(
        self,
        base64_image: str,
        mime_type: str,
        prompt: str,
        expect_json: bool,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://report-checker-pro.app",
        }
        request_data: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                        },
                    ],
                }
            ],
            "temperature": 0.1,
        }
        if expect_json:
            request_data["response_format"] = {"type": "json_object"}

        url = f"{self.config.base_url}/chat/completions"
        response = await self.client.post(url, headers=headers, json=request_data)
        response.raise_for_status()
        data = response.json()

        text = ""
        if "choices" in data and data["choices"]:
            text = str(data["choices"][0].get("message", {}).get("content", "")).strip()

        return {
            "text": text,
            "model": self.config.model,
            "provider": "openrouter",
            "usage": data.get("usage", {}),
        }

    async def _extract_via_direct(
        self,
        base64_image: str,
        mime_type: str,
        prompt: str,
        expect_json: bool,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        request_data: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                        },
                    ],
                }
            ],
            "temperature": 0.1,
        }
        if expect_json and self.config.provider == "openai":
            request_data["response_format"] = {"type": "json_object"}

        url = f"{self.config.base_url}/chat/completions"
        response = await self.client.post(url, headers=headers, json=request_data)
        response.raise_for_status()
        data = response.json()

        text = ""
        if "choices" in data and data["choices"]:
            text = str(data["choices"][0].get("message", {}).get("content", "")).strip()

        return {
            "text": text,
            "model": self.config.model,
            "provider": self.config.provider,
            "usage": data.get("usage", {}),
        }

    async def extract_label_fields_from_image(
        self,
        image_path: str | Path,
        base_text: str = "",
    ) -> dict[str, Any]:
        """Extract corrected label text + target fields with strict JSON output."""
        prompt = (
            "你是医疗器械标签OCR修订助手。请从图片中提取中文标签文本并修订OCR错误。"
            "必须返回严格JSON对象，且不允许Markdown。\n"
            "JSON schema:\n"
            "{\n"
            '  "raw_text": "完整标签文本，使用\\\\n分行",\n'
            '  "fields": {\n'
            '    "model_spec": "",\n'
            '    "production_date": "",\n'
            '    "batch_number": "",\n'
            '    "serial_number": "",\n'
            '    "registrant": "",\n'
            '    "registrant_address": ""\n'
            "  },\n"
            '  "confidence": 0.0,\n'
            '  "uncertain_fields": []\n'
            "}\n"
            "规则: 不确定字段留空；不要猜测。"
        )
        if base_text.strip():
            prompt += f"\n已知OCR文本(供参考，可纠错):\n{base_text}"

        result = await self.extract_text_from_image(
            image_path=image_path,
            prompt=prompt,
            expect_json=True,
        )
        if result.get("error"):
            return result

        payload = self._parse_json_content(str(result.get("text", "")))
        fields_payload = payload.get("fields", {}) if isinstance(payload, dict) else {}
        if not isinstance(fields_payload, dict):
            fields_payload = {}

        normalized_fields: dict[str, str] = {}
        allowed_keys = {
            "model_spec",
            "production_date",
            "batch_number",
            "serial_number",
            "registrant",
            "registrant_address",
        }
        for key in allowed_keys:
            normalized_fields[key] = str(fields_payload.get(key, "") or "").strip()

        confidence_value = payload.get("confidence", 0.0) if isinstance(payload, dict) else 0.0
        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "raw_text": str(payload.get("raw_text", "") or "").strip(),
            "fields": normalized_fields,
            "confidence": max(0.0, min(confidence, 1.0)),
            "uncertain_fields": payload.get("uncertain_fields", []),
            "provider": result.get("provider", self.config.provider),
            "model": result.get("model", self.config.model),
            "usage": result.get("usage", {}),
            "raw_response_text": result.get("text", ""),
        }

    async def extract_ptr_table_from_image(
        self,
        image_path: str | Path,
        headers_hint: list[str],
        base_rows: list[list[str]] | None = None,
        table_number: int | None = None,
        page_number: int | None = None,
    ) -> dict[str, Any]:
        """Extract structured PTR table rows from image with strict JSON output."""
        header_line = " | ".join(str(h or "").strip() for h in headers_hint if str(h or "").strip())
        table_tag = f"表{table_number}" if table_number else "参数表"
        page_tag = f"第{page_number}页" if page_number else "当前页"
        prompt = (
            "你是医疗器械技术要求文档的表格提取助手。"
            "请从图片中只提取目标参数表内容，输出严格JSON对象，不允许Markdown。\n"
            "JSON schema:\n"
            "{\n"
            '  "headers": ["参数", "型号", "常规数值", "标准设置", "允许误差"],\n'
            '  "rows": [["参数名","型号","常规数值","标准设置","允许误差"]],\n'
            '  "confidence": 0.0,\n'
            '  "notes": ""\n'
            "}\n"
            "规则:\n"
            "1) 必须按列输出，列数与headers一致；缺失填空字符串。\n"
            "2) 保留特殊字符（如μ、Ω、±、...、/）。\n"
            "3) 不要编造不存在的行。\n"
            f"4) 目标表: {table_tag}，页面: {page_tag}。\n"
        )
        if header_line:
            prompt += f"已知表头提示: {header_line}\n"
        if base_rows:
            seed_lines = []
            for row in base_rows[:8]:
                if not row:
                    continue
                seed_lines.append(" | ".join(str(cell or "").strip() for cell in row))
            if seed_lines:
                prompt += "已提取行(可能有误，仅供纠错):\n" + "\n".join(seed_lines)

        result = await self.extract_text_from_image(
            image_path=image_path,
            prompt=prompt,
            expect_json=True,
        )
        if result.get("error"):
            return result

        payload = self._parse_json_content(str(result.get("text", "")))
        if not isinstance(payload, dict):
            payload = {}

        parsed_headers = payload.get("headers", [])
        if not isinstance(parsed_headers, list):
            parsed_headers = []
        parsed_headers = [str(v or "").strip() for v in parsed_headers]

        parsed_rows = payload.get("rows", [])
        normalized_rows: list[list[str]] = []
        if isinstance(parsed_rows, list):
            for row in parsed_rows:
                if not isinstance(row, list):
                    continue
                normalized_rows.append([str(v or "").strip() for v in row])

        confidence_value = payload.get("confidence", 0.0)
        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "headers": parsed_headers,
            "rows": normalized_rows,
            "confidence": max(0.0, min(confidence, 1.0)),
            "notes": str(payload.get("notes", "") or "").strip(),
            "provider": result.get("provider", self.config.provider),
            "model": result.get("model", self.config.model),
            "usage": result.get("usage", {}),
            "raw_response_text": result.get("text", ""),
        }

    async def extract_text_with_retry(
        self,
        image_path: str | Path,
        prompt: str = "Extract all text from this image.",
        max_retries: int = 2,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await self.extract_text_from_image(image_path, prompt)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(f"VLM extraction attempt {attempt + 1} failed: {e}")
                if attempt == max_retries:
                    break
        return {
            "text": "",
            "error": f"Extraction failed after {max_retries} retries: {last_error}",
        }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _resolve_provider_and_key(
    provider_override: str | None = None,
) -> tuple[str, str]:
    """Resolve provider/key pair with optional provider preference."""
    openrouter_key = _non_empty_string(getattr(settings, "openrouter_api_key", ""))
    openai_key = _non_empty_string(getattr(settings, "openai_api_key", ""))
    deepseek_key = _non_empty_string(getattr(settings, "deepseek_api_key", ""))
    preferred_provider = _non_empty_string(
        provider_override or getattr(settings, "llm_provider", "openai")
    )

    if preferred_provider == "openrouter" and openrouter_key:
        return "openrouter", openrouter_key
    if preferred_provider == "openai" and openai_key:
        return "openai", openai_key
    if preferred_provider == "deepseek" and deepseek_key:
        return "deepseek", deepseek_key

    provider = ""
    api_key = ""
    if openrouter_key:
        provider = "openrouter"
        api_key = openrouter_key
    elif openai_key:
        provider = "openai"
        api_key = openai_key
    elif deepseek_key:
        provider = "deepseek"
        api_key = deepseek_key
    return provider, api_key


def create_vlm_service(
    model_override: str | None = None,
    provider_override: str | None = None,
) -> VLMService | None:
    """Create VLM service using available provider configuration."""
    model = _non_empty_string(model_override or getattr(settings, "llm_model", ""))
    if not model:
        model = "gpt-4o-mini"
    provider, api_key = _resolve_provider_and_key(provider_override=provider_override)
    if not provider or not api_key:
        logger.warning("VLM service requested but no API key configured")
        return None

    config = VLMServiceConfig(
        provider=provider,
        model=model,
        api_key=api_key,
    )
    return VLMService(config=config)


async def extract_text_with_vlm(
    image_path: str | Path,
    prompt: str = "Extract all text from this image.",
) -> dict[str, Any]:
    service = create_vlm_service()
    if not service:
        return {"text": "", "error": "VLM not configured"}
    return await service.extract_text_from_image(image_path, prompt)
