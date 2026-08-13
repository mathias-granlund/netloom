import logging

from netloom.core.config import Settings
from netloom.logging.setup import (
    NO_LOGGING_LEVEL,
    LoggerConfig,
    LoggingManager,
    configure_logging,
)


def test_logging_manager_is_not_singleton():
    a = LoggingManager(LoggerConfig(root_name="t1", console=False))
    b = LoggingManager(LoggerConfig(root_name="t2", console=False))
    assert a is not b


def test_get_logger_prefix_and_inheritance():
    mgr = LoggingManager(LoggerConfig(root_name="netloomtest", console=False))
    child = mgr.get_logger("module")
    assert child.name == "netloomtest.module"
    assert child.level == logging.NOTSET
    assert child.propagate is True


def test_set_level_updates_handlers():
    mgr = LoggingManager(LoggerConfig(root_name="netloomtest2", console=True))
    assert any(
        isinstance(handler, logging.StreamHandler) for handler in mgr.root.handlers
    )
    mgr.set_level(logging.DEBUG)
    assert mgr.root.level == logging.DEBUG
    for handler in mgr.root.handlers:
        assert handler.level == logging.DEBUG


def test_configure_logging_with_file(tmp_path):
    settings = Settings(
        log_level="DEBUG",
        log_to_file=True,
        log_file=tmp_path / "app.log",
    )
    mgr = configure_logging(settings, root_name="envtest")
    assert mgr.root.level == logging.DEBUG
    assert any(
        isinstance(handler, logging.FileHandler) for handler in mgr.root.handlers
    )


def test_configure_logging_none_suppresses_console_and_file(tmp_path, capsys):
    log_file = tmp_path / "app.log"
    settings = Settings(
        log_level="NONE",
        log_to_file=True,
        log_file=log_file,
    )

    mgr = configure_logging(settings, root_name="none_test")
    log = mgr.get_logger("module")
    log.critical("hidden")

    captured = capsys.readouterr()
    assert captured.err == ""
    assert mgr.root.level == NO_LOGGING_LEVEL
    assert mgr.root.handlers == []
    assert not log_file.exists()
