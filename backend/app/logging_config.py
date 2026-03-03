"""
Logging Configuration Module
Centralizes logging setup for the application.
"""

import logging
import sys
from typing import Final

# Log format constants
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure application logging with consistent format.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured root logger instance
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
    )
    return logging.getLogger("report-checker-pro")
