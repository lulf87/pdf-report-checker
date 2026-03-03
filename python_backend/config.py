"""
配置管理
支持环境变量和.env文件
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用路径
    BASE_DIR: Path = Path(__file__).parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TEMP_DIR: Path = BASE_DIR / "temp"

    # API密钥
    OPENROUTER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None

    # LLM配置
    LLM_MODEL: str = "google/gemini-2.0-flash-exp"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0

    # OpenRouter配置
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # 功能开关
    ENABLE_LLM_POST_PROCESSING: bool = True
    ENABLE_LLAMAPARSE_FALLBACK: bool = False

    # LLM比对功能开关
    ENABLE_LLM_COMPARISON: bool = False  # 是否启用LLM进行字段比对
    LLM_COMPARISON_MODE: str = "fallback"  # 模式: "fallback"(OCR失败时调用LLM), "enhance"(总是用LLM增强), "disabled"(禁用)
    LLM_RETRY_ON_FAILURE: bool = True  # OCR失败时是否尝试LLM
    LLM_CONFIDENCE_THRESHOLD: float = 0.8  # LLM结果置信度阈值

    # 视觉大模型OCR配置
    ENABLE_VISION_LLM_OCR: bool = True  # 启用视觉大模型OCR作为fallback
    VISION_LLM_MODE: str = "fallback"  # 模式: "primary"(优先使用), "fallback"(传统OCR失败时使用), "disabled"(禁用)
    VISION_LLM_FALLBACK_THRESHOLD: int = 3  # 传统OCR提取字段数低于3个时触发fallback

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 配置实例
settings = get_settings()

# 检查LLM功能是否可用
def is_llm_enabled() -> bool:
    """检查LLM功能是否启用"""
    return (
        settings.ENABLE_LLM_POST_PROCESSING and
        (settings.OPENROUTER_API_KEY or settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)
    )


def is_llm_comparison_enabled() -> bool:
    """检查是否启用LLM比对功能"""
    return (
        settings.ENABLE_LLM_COMPARISON and
        is_llm_enabled() and
        settings.LLM_COMPARISON_MODE != "disabled"
    )


# 获取默认LLM提供商
def get_llm_provider() -> str:
    """获取默认LLM提供商"""
    # OpenRouter优先
    if settings.OPENROUTER_API_KEY:
        return "openrouter"
    elif settings.ANTHROPIC_API_KEY:
        return "anthropic"
    elif settings.OPENAI_API_KEY:
        return "openai"
    else:
        return "none"


# 判断是否使用OpenRouter
def is_openrouter_model(model: str) -> bool:
    """判断模型是否需要通过OpenRouter访问"""
    openrouter_prefixes = [
        "google/",
        "anthropic/",
        "openai/",
        "meta-llama/",
        "mistralai/",
        "deepseek/",
        "qwen/",
    ]
    return any(model.startswith(prefix) for prefix in openrouter_prefixes)


# 检查视觉大模型OCR是否启用
def is_vision_llm_ocr_enabled() -> bool:
    """检查是否启用视觉大模型OCR功能"""
    return (
        settings.ENABLE_VISION_LLM_OCR and
        settings.VISION_LLM_MODE != "disabled" and
        (settings.OPENROUTER_API_KEY or settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)
    )
