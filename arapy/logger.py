# logger.py
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class LoggerConfig:
    """
    Central config for the app logger.

    root_name:
        Name of the "root" logger for your application namespace.
        Child loggers will be created under this namespace.

    level:
        Default level for the app root logger at startup (typically INFO).

    log_file:
        If set, logs will also be written to this file.

    console:
        If True, logs will be emitted to stderr.

    fmt / datefmt:
        Formatter settings.
    """
    root_name: str = "logger"
    level: int = logging.INFO
    log_file: Optional[Path] = None
    console: bool = True
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"

class ColorFormatter(logging.Formatter):
    BLUE = "\033[34m"
    RED = "\033[31m"
    RESET = "\033[0m"

    LEVEL_COLORS = {
        logging.INFO: BLUE,
        logging.DEBUG: RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno)
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)

class AppLogger:
    """
    Singleton-ish logger manager.

    Key idea (from the article):
    - Create child loggers per module.
    - Do NOT set levels on child loggers (leave NOTSET) so they inherit.
    - Flip the parent/root logger to DEBUG mid-run when needed. :contentReference[oaicite:2]{index=2}
    """

    _instance: Optional["AppLogger"] = None

    def __new__(cls, config: Optional[LoggerConfig] = None) -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[LoggerConfig] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.config = config or LoggerConfig()
        self._root_logger = logging.getLogger(self.config.root_name)

        # Ensure our app-root logger doesn't bubble into the global root logger
        # (helps avoid duplicate output if the host app configures logging too).
        self._root_logger.propagate = False

        self._configure_root_logger()
        self._initialized = True

    def _configure_root_logger(self) -> None:
        self._root_logger.setLevel(self.config.level)

        # IMPORTANT: handlers also have levels; if handler level is higher than
        # logger level, messages can still be filtered out. :contentReference[oaicite:3]{index=3}
        if self.config.console:
            self._add_console_handler()

        if self.config.log_file is not None:
            self._add_file_handler(self.config.log_file)

    def _formatter(self) -> logging.Formatter:
        return logging.Formatter(self.config.fmt, datefmt=self.config.datefmt)

    def _has_handler(self, handler_type: type, *, file_path: Optional[Path] = None) -> bool:
        for h in self._root_logger.handlers:
            if isinstance(h, handler_type):
                if file_path is None:
                    return True
                # For file handlers, avoid duplicates by matching the target path.
                if isinstance(h, logging.FileHandler):
                    try:
                        return Path(h.baseFilename).resolve() == file_path.resolve()
                    except Exception:
                        # If anything is odd, fall back to "same type exists" semantics.
                        return True
        return False

    def _add_console_handler(self) -> None:
        if self._has_handler(logging.StreamHandler):
            return
        h = logging.StreamHandler(stream=sys.stderr)
        h.setLevel(self._root_logger.level)
        h.setFormatter(ColorFormatter(self.config.fmt, datefmt=self.config.datefmt))
        self._root_logger.addHandler(h)

    def _add_file_handler(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if self._has_handler(logging.FileHandler, file_path=path):
            return
        h = logging.FileHandler(filename=str(path), encoding="utf-8")
        h.setLevel(self._root_logger.level)
        h.setFormatter(self._formatter())
        self._root_logger.addHandler(h)

    def get_logger(self, logger_name: str) -> logging.Logger:
        """
        Return a child logger for a module.

        We leave the child logger's level as NOTSET so it inherits the
        app-root logger's level. :contentReference[oaicite:4]{index=4}
        """
        # Normalize names: allow "__name__" input, or already-prefixed strings.
        if logger_name.startswith(self.config.root_name + "."):
            name = logger_name
        else:
            name = f"{self.config.root_name}.{logger_name}"

        child = logging.getLogger(name)
        child.setLevel(logging.NOTSET)     # inherit from app root
        child.propagate = True            # propagate to app-root logger
        return child

    def set_level(self, level: int) -> None:
        """
        Set app-root logger level mid-run; update handler levels too.
        """
        self._root_logger.setLevel(level)
        for h in self._root_logger.handlers:
            h.setLevel(level)

    def set_debug_mode(self, debug_mode: bool = True) -> None:
        """
        Toggle DEBUG mid-run (the main trick in the article). :contentReference[oaicite:5]{index=5}
        """
        self.set_level(logging.DEBUG if debug_mode else self.config.level)

    @property
    def root(self) -> logging.Logger:
        return self._root_logger


def build_logger_from_env(
    *,
    root_name: str = "logger",
    default_level: int = logging.INFO,
    env_flag: str = "DEBUG",
    env_log_file: str = "LOG_FILE",
) -> AppLogger:
    """
    Convenience helper:
    - If env DEBUG=1/true/yes/on => start in DEBUG
    - If env LOG_FILE=/path/to/file.log => also log to file
    """
    debug_raw = os.getenv(env_flag, "")
    debug_on = debug_raw.strip().lower() in {"1", "true", "yes", "on"}

    log_file_raw = os.getenv(env_log_file)
    log_file = Path(log_file_raw) if log_file_raw else None

    cfg = LoggerConfig(
        root_name=root_name,
        level=logging.DEBUG if debug_on else default_level,
        log_file=log_file,
        console=True,
    )
    return AppLogger(cfg)