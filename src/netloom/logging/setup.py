from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from netloom.core.config import Settings

NO_LOGGING_LEVEL = logging.CRITICAL + 1


@dataclass(frozen=True)
class LoggerConfig:
    root_name: str = "netloom"
    level: int = logging.INFO
    console: bool = True
    log_file: Path | None = None
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


class ColorFormatter(logging.Formatter):
    BLUE = "\033[34m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    ORANGE = "\033[38;5;214m"
    RESET = "\033[0m"

    LEVEL_COLORS = {
        logging.INFO: GREEN,
        logging.DEBUG: BLUE,
        logging.ERROR: ORANGE,
        logging.WARNING: YELLOW,
        logging.CRITICAL: RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        original = record.levelname
        color = self.LEVEL_COLORS.get(record.levelno)
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original


class LoggingManager:
    def __init__(self, config: LoggerConfig):
        self.config = config
        self._root_logger = logging.getLogger(config.root_name)
        self._root_logger.propagate = False
        self._configure()

    def _configure(self) -> None:
        self._root_logger.handlers.clear()
        self._root_logger.setLevel(self.config.level)

        if self.config.console:
            console = logging.StreamHandler(stream=sys.stderr)
            console.setLevel(self.config.level)
            console.setFormatter(
                ColorFormatter(self.config.fmt, datefmt=self.config.datefmt)
            )
            self._root_logger.addHandler(console)

        if self.config.log_file is not None:
            self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.config.log_file, encoding="utf-8")
            file_handler.setLevel(self.config.level)
            file_handler.setFormatter(
                logging.Formatter(self.config.fmt, datefmt=self.config.datefmt)
            )
            self._root_logger.addHandler(file_handler)

    def get_logger(self, logger_name: str) -> logging.Logger:
        if logger_name.startswith(self.config.root_name):
            name = logger_name
        else:
            name = f"{self.config.root_name}.{logger_name}"
        child = logging.getLogger(name)
        child.setLevel(logging.NOTSET)
        child.propagate = True
        return child

    def set_level(self, level: int) -> None:
        self._root_logger.setLevel(level)
        for handler in self._root_logger.handlers:
            handler.setLevel(level)

    @property
    def root(self) -> logging.Logger:
        return self._root_logger


LOG_LEVELS = {
    "NONE": NO_LOGGING_LEVEL,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(
    settings: Settings, *, root_name: str = "netloom"
) -> LoggingManager:
    level = LOG_LEVELS.get(settings.log_level.strip().upper(), logging.INFO)
    logging_enabled = level != NO_LOGGING_LEVEL
    log_file = settings.log_file if logging_enabled and settings.log_to_file else None
    return LoggingManager(
        LoggerConfig(
            root_name=root_name,
            level=level,
            console=logging_enabled,
            log_file=log_file,
        )
    )
