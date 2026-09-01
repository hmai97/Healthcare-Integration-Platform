"""Logging configuration for the healthcare integration platform."""

import logging
from typing import Any


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("healthcare.integration")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
