"""
LLM Service for text enhancement.

Provides LLM integration for text enhancement and verification
with support for OpenRouter API and multiple providers.
"""

import logging
from enum import Enum
from typing import Any, Literal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class LLMMode(str, Enum):
    """LLM processing modes."""

    ENHANCE = "enhance"  # Always use LLM
    FALLBACK = "fallback"  # Use LLM only when OCR fails
    DISABLED = "disabled"  # Never use LLM


class LLMServiceConfig:
    """Configuration for LLM service.

    Attributes:
        provider: LLM provider to use
        model: Model identifier
        api_key: API key for the provider
        base_url: Base URL for API requests
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        model: str = "gpt-4o-mini",
        api_key: str = "",
        base_url: str = "",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize LLM service config.

        Args:
            provider: LLM provider
            model: Model identifier
            api_key: API key
            base_url: Optional base URL override
            timeout: Request timeout
            max_retries: Maximum retry attempts
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Set base URL based on provider
        if base_url:
            self.base_url = base_url
        elif provider == LLMProvider.OPENAI:
            self.base_url = "https://api.openai.com/v1"
        elif provider == LLMProvider.DEEPSEEK:
            self.base_url = "https://api.deepseek.com/v1"
        else:
            self.base_url = ""

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.api_key and self.model)


class LLMService:
    """LLM service for text enhancement and verification.

    Supports multiple providers through OpenRouter-compatible API.
    """

    def __init__(
        self,
        config: LLMServiceConfig | None = None,
    ):
        """Initialize LLM service.

        Args:
            config: Service configuration (uses settings if None)
        """
        if config is None:
            # Create config from settings
            provider = LLMProvider.OPENAI
            if settings.llm_provider == "deepseek":
                provider = LLMProvider.DEEPSEEK

            config = LLMServiceConfig(
                provider=provider,
                model=settings.llm_model,
                api_key=settings.openai_api_key
                if provider == LLMProvider.OPENAI
                else settings.deepseek_api_key,
            )

        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout)
            limits = httpx.Limits(
                max_connections=5,
                max_keepalive_connections=5,
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
            )
        return self._client

    async def enhance_text(
        self,
        text: str,
        context: str = "",
    ) -> dict[str, str]:
        """Enhance text using LLM.

        Args:
            text: Text to enhance
            context: Additional context for enhancement

        Returns:
            Dictionary with enhanced_text and metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        if not self.config.is_configured:
            return {"enhanced_text": text, "error": "LLM not configured"}

        # Build prompt
        system_prompt = """You are a text processing assistant. Your task is to enhance and correct text extracted from Chinese technical documents (especially PDFs and OCR output).

Rules:
1. Preserve all technical meaning and accuracy
2. Fix OCR errors (similar characters, spacing issues)
3. Correct formatting inconsistencies
4. Preserve Chinese characters exactly as they appear
5. Output ONLY the enhanced text, no explanations
"""

        user_prompt = f"Enhance the following text:\n\n{text}"
        if context:
            user_prompt += f"\n\nContext: {context}"

        # Build request
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,  # Lower temperature for more consistent output
            "max_tokens": 2000,
        }

        # Make request
        url = f"{self.config.base_url}/chat/completions"
        response = await self.client.post(
            url, headers=headers, json=request_data
        )

        response.raise_for_status()

        data = response.json()

        # Extract enhanced text
        if "choices" in data and data["choices"]:
            enhanced_text = data["choices"][0]["message"]["content"].strip()
        else:
            enhanced_text = text

        return {
            "enhanced_text": enhanced_text,
            "model": self.config.model,
            "usage": data.get("usage", {}),
        }

    async def verify_extraction(
        self,
        text: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        """Verify extracted text using LLM.

        Args:
            text: Text to verify
            expected_fields: List of expected field names

        Returns:
            Dictionary with verification results
        """
        if not self.config.is_configured:
            return {"verified": False, "error": "LLM not configured"}

        # Build prompt
        field_list = ", ".join(expected_fields)
        system_prompt = f"""You are a document verification assistant. Check if the following text contains the expected fields.

Expected fields: {field_list}

Rules:
1. Return JSON format: {{"verified": true/false, "missing_fields": [], "found_fields": [], "issues": []}}
2. Check for each expected field by name
3. Consider variations in naming and formatting
4. Output ONLY valid JSON, no other text
"""

        user_prompt = f"Verify this text contains the expected fields:\n\n{text}"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,  # Low temperature for consistent JSON output
            "response_format": {"type": "json_object"},
        }

        url = f"{self.config.base_url}/chat/completions"
        response = await self.client.post(
            url, headers=headers, json=request_data
        )

        response.raise_for_status()

        data = response.json()

        # Extract verification result
        if "choices" in data and data["choices"]:
            import json

            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            return {"verified": False, "error": "No response from LLM"}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def create_llm_service(mode: LLMMode = LLMMode.DISABLED) -> LLMService | None:
    """Create LLM service based on mode.

    Args:
        mode: LLM processing mode

    Returns:
        LLMService instance or None if disabled
    """
    if mode == LLMMode.DISABLED:
        return None

    # Create config from settings
    provider = LLMProvider.OPENAI
    if settings.llm_provider == "deepseek":
        provider = LLMProvider.DEEPSEEK

    api_key = ""
    if provider == LLMProvider.OPENAI:
        api_key = settings.openai_api_key
    elif provider == LLMProvider.DEEPSEEK:
        api_key = settings.deepseek_api_key

    if not api_key:
        logger.warning("LLM service requested but no API key configured")
        return None

    config = LLMServiceConfig(
        provider=provider,
        model=settings.llm_model,
        api_key=api_key,
    )

    return LLMService(config=config)
