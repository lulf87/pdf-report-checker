"""
Application Configuration Module
Manages environment variables and application settings using pydantic-settings.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_mode: Literal["enhance", "fallback", "disabled"] = Field(
        default="fallback",
        description="LLM processing mode: enhance (always use), fallback (OCR only on error), disabled (OCR only)",
    )
    llm_provider: Literal["openai", "deepseek"] = Field(
        default="openai",
        description="LLM provider: openai or deepseek",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM enhancement",
    )
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key for LLM enhancement",
    )
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key for vision-based LLM enhancement",
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model identifier",
    )
    vlm_primary_model: str = Field(
        default="qwen/qwen3-vl-8b-instruct",
        description="Primary (low-cost) VLM model for OCR correction",
    )
    vlm_secondary_model: str = Field(
        default="qwen/qwen3-vl-30b-a3b-instruct",
        description="Secondary (higher-accuracy) VLM model for OCR correction fallback",
    )
    vlm_secondary_trigger_confidence: float = Field(
        default=0.75,
        description="Trigger secondary VLM when primary confidence is below this threshold",
    )
    ptr_table_vlm_enabled: bool = Field(
        default=False,
        description="Enable VLM enhancement for complex PTR parameter tables",
    )
    ptr_table_vlm_min_rows: int = Field(
        default=20,
        description="Minimum row count to consider VLM enhancement for PTR tables",
    )
    ptr_table_vlm_max_pages: int = Field(
        default=4,
        description="Maximum pages to send for one PTR table VLM enhancement",
    )

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, description="Server port")

    # OCR Configuration
    ocr_language: str = Field(
        default="ch",
        description="OCR language: ch (Chinese), en (English), or mixed",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
