"""
Tests for LLM and VLM services.

Tests are designed to run without actual API calls using mocking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.llm_service import (
    LLMProvider,
    LLMMode,
    LLMServiceConfig,
    LLMService,
    create_llm_service,
)
from app.services.llm_vision_service import (
    VLMServiceConfig,
    VLMService,
    create_vlm_service,
    extract_text_with_vlm,
)


# ============================================================================
# LLM Service Config Tests
# ============================================================================


class TestLLMServiceConfig:
    """Tests for LLMServiceConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LLMServiceConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4o-mini"
        assert config.api_key == ""
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_openai_base_url(self):
        """Test OpenAI base URL is set correctly."""
        config = LLMServiceConfig(provider=LLMProvider.OPENAI)
        assert config.base_url == "https://api.openai.com/v1"

    def test_deepseek_base_url(self):
        """Test DeepSeek base URL is set correctly."""
        config = LLMServiceConfig(provider=LLMProvider.DEEPSEEK)
        assert config.base_url == "https://api.deepseek.com/v1"

    def test_custom_base_url(self):
        """Test custom base URL override."""
        config = LLMServiceConfig(base_url="https://custom.api.com/v1")
        assert config.base_url == "https://custom.api.com/v1"

    def test_is_configured_with_api_key(self):
        """Test is_configured returns True with API key."""
        config = LLMServiceConfig(api_key="test-key")
        assert config.is_configured is True

    def test_is_configured_without_api_key(self):
        """Test is_configured returns False without API key."""
        config = LLMServiceConfig()
        assert config.is_configured is False

    def test_is_configured_without_model(self):
        """Test is_configured returns False without model."""
        config = LLMServiceConfig(api_key="test-key", model="")
        assert config.is_configured is False


# ============================================================================
# LLM Service Tests
# ============================================================================


class TestLLMService:
    """Tests for LLMService."""

    def test_initialization_with_config(self):
        """Test service initialization with custom config."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)
        assert service.config == config

    def test_client_lazy_initialization(self):
        """Test HTTP client is lazily initialized."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)
        assert service._client is None
        client = service.client
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_enhance_text_not_configured(self):
        """Test enhance_text returns original text when not configured."""
        config = LLMServiceConfig()  # No API key
        service = LLMService(config=config)

        result = await service.enhance_text("test text")

        assert result["enhanced_text"] == "test text"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_enhance_text_success(self):
        """Test successful text enhancement."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)

        # Mock the HTTP client at the class level
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "enhanced text"}}],
            "usage": {"total_tokens": 100},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Patch the _client attribute directly
        service._client = mock_client

        result = await service.enhance_text("test text")

        assert result["enhanced_text"] == "enhanced text"
        assert result["model"] == config.model

    @pytest.mark.asyncio
    async def test_enhance_text_with_context(self):
        """Test text enhancement with context."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "enhanced"}}],
            "usage": {},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        service._client = mock_client

        result = await service.enhance_text("test", context="technical document")

        assert result["enhanced_text"] == "enhanced"

    @pytest.mark.asyncio
    async def test_verify_extraction_not_configured(self):
        """Test verify_extraction returns error when not configured."""
        config = LLMServiceConfig()  # No API key
        service = LLMService(config=config)

        result = await service.verify_extraction("text", ["field1"])

        assert result["verified"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_verify_extraction_success(self):
        """Test successful extraction verification."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"verified": true, "missing_fields": [], "found_fields": ["field1"]}'
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        service._client = mock_client

        result = await service.verify_extraction("text with field1", ["field1"])

        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing HTTP client."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)

        # Initialize client
        _ = service.client

        await service.close()

        assert service._client is None


# ============================================================================
# VLM Service Config Tests
# ============================================================================


class TestVLMServiceConfig:
    """Tests for VLMServiceConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VLMServiceConfig()
        assert config.provider == "openrouter"
        assert config.model == "google/gemini-2.0-flash-exp"
        assert config.api_key == ""
        assert config.timeout == 60

    def test_openrouter_base_url(self):
        """Test OpenRouter base URL is set correctly."""
        config = VLMServiceConfig(provider="openrouter")
        assert config.base_url == "https://openrouter.ai/api/v1"

    def test_custom_base_url(self):
        """Test custom base URL override."""
        config = VLMServiceConfig(base_url="https://custom.api.com/v1")
        assert config.base_url == "https://custom.api.com/v1"

    def test_is_configured_with_api_key(self):
        """Test is_configured returns True with API key."""
        config = VLMServiceConfig(api_key="test-key")
        assert config.is_configured is True

    def test_is_configured_without_api_key(self):
        """Test is_configured returns False without API key."""
        config = VLMServiceConfig()
        assert config.is_configured is False


# ============================================================================
# VLM Service Tests
# ============================================================================


class TestVLMService:
    """Tests for VLMService."""

    def test_initialization_with_config(self):
        """Test service initialization with custom config."""
        config = VLMServiceConfig(api_key="test-key")
        service = VLMService(config=config)
        assert service.config == config

    def test_client_lazy_initialization(self):
        """Test HTTP client is lazily initialized."""
        config = VLMServiceConfig(api_key="test-key")
        service = VLMService(config=config)
        assert service._client is None
        client = service.client
        assert client is not None

    @pytest.mark.asyncio
    async def test_extract_text_not_configured(self):
        """Test extract_text_from_image returns error when not configured."""
        config = VLMServiceConfig()  # No API key
        service = VLMService(config=config)

        result = await service.extract_text_from_image("/fake/path.png")

        assert result["text"] == ""
        assert "error" in result

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing HTTP client."""
        config = VLMServiceConfig(api_key="test-key")
        service = VLMService(config=config)

        # Initialize client
        _ = service.client

        await service.close()

        assert service._client is None


# ============================================================================
# Convenience Functions Tests
# ============================================================================


class TestCreateLLMService:
    """Tests for create_llm_service function."""

    def test_create_disabled_mode(self):
        """Test creating service in disabled mode returns None."""
        result = create_llm_service(mode=LLMMode.DISABLED)
        assert result is None


class TestCreateVLMService:
    """Tests for create_vlm_service function."""

    def test_create_without_api_key(self):
        """Test creating service without API key returns None."""
        with patch("app.services.llm_vision_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = ""
            result = create_vlm_service()
            assert result is None


class TestExtractTextWithVLM:
    """Tests for extract_text_with_vlm convenience function."""

    @pytest.mark.asyncio
    async def test_extract_without_service(self):
        """Test extraction returns error when service not available."""
        with patch("app.services.llm_vision_service.create_vlm_service") as mock_create:
            mock_create.return_value = None

            result = await extract_text_with_vlm("/fake/path.png")

            assert result["text"] == ""
            assert "error" in result


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_llm_config_with_empty_strings(self):
        """Test config with empty strings."""
        config = LLMServiceConfig(api_key="", model="")
        assert config.is_configured is False

    def test_vlm_config_with_empty_strings(self):
        """Test VLM config with empty strings."""
        config = VLMServiceConfig(api_key="")
        assert config.is_configured is False

    @pytest.mark.asyncio
    async def test_llm_enhance_empty_text(self):
        """Test enhancing empty text."""
        config = LLMServiceConfig(api_key="test-key")
        service = LLMService(config=config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}],
            "usage": {},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        service._client = mock_client

        result = await service.enhance_text("")

        assert result["enhanced_text"] == ""

    def test_llm_provider_enum_values(self):
        """Test LLMProvider enum has expected values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.DEEPSEEK.value == "deepseek"

    def test_llm_mode_enum_values(self):
        """Test LLMMode enum has expected values."""
        assert LLMMode.ENHANCE.value == "enhance"
        assert LLMMode.FALLBACK.value == "fallback"
        assert LLMMode.DISABLED.value == "disabled"
