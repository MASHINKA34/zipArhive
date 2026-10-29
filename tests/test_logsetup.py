from __future__ import annotations

import faulthandler
import logging
import os
import sys
import threading

import pytest

from core import logsetup


@pytest.fixture
def isolated_logging(monkeypatch):
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    hooks = (sys.excepthook, threading.excepthook, sys.unraisablehook)
    state = {"configured": False, "crash_file": None}
    monkeypatch.setattr(logsetup, "_state", state)
    yield
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers = handlers
    root.setLevel(level)
    sys.excepthook, threading.excepthook, sys.unraisablehook = hooks
    faulthandler.disable()
    if state.get("crash_file") is not None:
        state["crash_file"].close()


def test_resolve_level():
    assert logsetup.resolve_level(None) == (logging.INFO, None)
    assert logsetup.resolve_level("debug") == (logging.DEBUG, None)
    assert logsetup.resolve_level("WARN") == (logging.WARNING, None)
    assert logsetup.resolve_level("verbose") == (logging.INFO, "VERBOSE")


def test_setup_logging_writes_file_with_job(tmp_path, monkeypatch,
                                            isolated_logging):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    path = logsetup.setup_logging(str(tmp_path))
    assert path == os.path.join(str(tmp_path), logsetup.LOG_FILE_NAME)
    with logsetup.job_context("pack-7"):
        logging.getLogger("quickzip.test").info("hello %s", "мир")
    logging.getLogger("quickzip.test").debug("outside job")
    for handler in logging.getLogger().handlers:
        handler.flush()
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    assert "INFO    [quickzip.test] [pack-7] hello мир" in text
    assert "DEBUG   [quickzip.test] outside job" in text
    assert os.path.exists(
        os.path.join(str(tmp_path), logsetup.CRASH_FILE_NAME)
    )


def test_excepthook_logs_traceback(tmp_path, isolated_logging, caplog):
    logsetup.setup_logging(str(tmp_path))
    try:
        raise ValueError("сломалось")
    except ValueError:
        info = sys.exc_info()
    with caplog.at_level("ERROR", logger="quickzip.crash"):
        sys.excepthook(*info)
    record = caplog.records[-1]
    assert record.levelno == logging.CRITICAL
    assert "ValueError: сломалось" in record.getMessage()
    assert record.exc_info is not None


def test_unknown_level_is_reported(tmp_path, monkeypatch, isolated_logging,
                                   caplog):
    monkeypatch.setenv("LOG_LEVEL", "chatty")
    with caplog.at_level("WARNING", logger="quickzip.log"):
        logsetup.setup_logging(str(tmp_path))
    assert any("Unknown LOG_LEVEL" in record.getMessage()
               for record in caplog.records)
