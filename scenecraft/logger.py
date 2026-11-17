"""Logging infrastructure for Scenecraft with rotating file storage."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from scenecraft.config import get_config


_LOGGER_INITIALIZED = False


def get_log_dir() -> Path:
    """Return user log directory and ensure it exists."""
    cfg = get_config()
    log_dir = cfg.log_dir
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to local logs directory if system log dir is inaccessible
        log_dir = Path.cwd() / ".logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    """Return path to primary rotating log file."""
    return get_log_dir() / "scenecraft.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Initialize root/scenecraft rotating file logger."""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger("scenecraft")
    if _LOGGER_INITIALIZED:
        return logger

    logger.setLevel(level)

    try:
        log_file = get_log_file_path()
        handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5 MB rotation
            backupCount=3,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        _LOGGER_INITIALIZED = True
    except Exception:
        # Fail gracefully without crashing application
        pass

    return logger


def get_latest_log_lines(max_lines: int = 50) -> List[str]:
    """Return the last N lines of the current log file safely."""
    log_file = get_log_file_path()
    if not log_file.is_file():
        return []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return [line.rstrip("\r\n") for line in lines[-max_lines:]]
    except Exception:
        return []
