"""
VLM (Vision Language Model) Service for image-based text extraction.

Provides integration with vision-capable LLMs for extracting text from
images when traditional OCR fails or needs enhancement.
"""

import logging
from base64 import b64encode
from pathlib import Path
from typing import Literal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VLMServiceConfig:
    """Configuration for VLM service.

    Attributes:
        provider: VLM provider
        model: Model identifier
        api_key: API key
        base_url: Base URL for API requests
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "google/gemini-2.0-flash-exp",
        api_key: str = "",
        base_url: str = "",
        timeout: int = 60,
    ):
        """Initialize VLM service config.

        Args:
            provider: Service provider (openrouter, openai, etc.)
            model: Model identifier
            api_key: API key
            base_url: Optional base URL override
            timeout: Request timeout
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

        # Set base URL
        if base_url:
            self.base_url = base_url
        elif provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1"
        else:
            self.base_url = ""

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.api_key)


class VLMService:
    """VLM service for image-based text extraction.

    Uses vision-capable LLMs to extract text from images
    when traditional OCR fails or needs enhancement.
    """

    def __init__(
        self,
        config: VLMServiceConfig | None = None,
    ):
        """Initialize VLM service.

        Args:
            config: Service configuration (uses settings if None)
        """
        if config is None:
            config = VLMServiceConfig(
                model=settings.llm_model,
                api_key="",  # Would use openrouter_api_key in production
            )

        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    def _encode_image(self, image_path: str | Path) -> str:
        """Encode image to base64.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string
        """
        image_path = Path(image_path)

        with image_path.open("rb") as f:
            image_data = f.read()
            return b64encode(image_data).decode("utf-8")

    async def extract_text_from_image(
        self,
        image_path: str | Path,
        prompt: str = "Extract all text from this image. Preserve formatting and structure.",
    ) -> dict[str, str]:
        """Extract text from image using VLM.

        Args:
            image_path: Path to image file
            prompt: Prompt for the VLM

        Returns:
            Dictionary with extracted text and metadata

        Raises:
            httpx.HTTPError: If API request fails
        """
        if not self.config.is_configured:
            return {"text": "", "error": "VLM not configured"}

        # Encode image
        base64_image = self._encode_image(image_path)

        # Determine MIME type
        image_path = Path(image_path)
        mime_type = "image/png"
        if image_path.suffix.lower() in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"

        # Build request based on provider
        if self.config.provider == "openrouter":
            return await self._extract_via_openrouter(
                base64_image, mime_type, prompt
            )
        else:
            return await self._extract_via_direct(
                base64_image, mime_type, prompt
            )

    async def _extract_via_openrouter(
        self,
        base64_image: str,
        mime_type: str,
        prompt: str,
    ) -> dict[str, str]:
        """Extract text using OpenRouter API.

        Args:
            base64_image: Base64 encoded image
            mime_type: Image MIME type
            prompt: User prompt

        Returns:
            Dictionary with extracted text and metadata
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://report-checker-pro.app",
        }

        request_data = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:{mime_type};base64,{base64_image}",
                        },
                    ],
                }
            ],
        }

        url = f"{self.config.base_url}/chat/completions"
        response = await self.client.post(url, headers=headers, json=request_data)

        response.raise_for_status()

        data = response.json()

        # Extract text from response
        if "choices" in data and data["choices"]:
            text = data["choices"][0]["message"]["content"].strip()
        else:
            text = ""

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
    ) -> dict[str, str]:
        """Extract text using direct provider API.

        Args:
            base64_image: Base64 encoded image
            mime_type: Image MIME type
            prompt: User prompt

        Returns:
            Dictionary with extracted text and metadata
        """
        # Placeholder for direct API integration
        # This would need to be implemented per provider
        return {
            "text": "",
            "error": "Direct API not implemented for this provider",
        }

    async def extract_text_with_retry(
        self,
        image_path: str | Path,
        prompt: str = "Extract all text from this image.",
        max_retries: int = 2,
    ) -> dict[str, str]:
        """Extract text with retry logic.

        Args:
            image_path: Path to image file
            prompt: Prompt for the VLM
            max_retries: Maximum retry attempts

        Returns:
            Dictionary with extracted text and metadata
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self.extract_text_from_image(image_path, prompt)
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"VLM extraction attempt {attempt + 1} failed: {e}"
                )

                if attempt == max_retries:
                    break

        return {
            "text": "",
            "error": f"Extraction failed after {max_retries} retries: {last_error}",
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def create_vlm_service() -> VLMService | None:
    """Create VLM service based on settings.

    Returns:
        VLMService instance or None if not configured
    """
    if not settings.openrouter_api_key:
        logger.warning("VLM service requested but OpenRouter API key not configured")
        return None

    config = VLMServiceConfig(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
    )

    return VLMService(config=config)


async def extract_text_with_vlm(
    image_path: str | Path,
    prompt: str = "Extract all text from this image.",
) -> dict[str, str]:
    """Convenience function to extract text using VLM.

    Args:
        image_path: Path to image file
        prompt: Prompt for the VLM

    Returns:
        Dictionary with extracted text and metadata
    """
    service = create_vlm_service()
    if not service:
        return {"text": "", "error": "VLM not configured"}

    return await service.extract_text_from_image(image_path, prompt)
