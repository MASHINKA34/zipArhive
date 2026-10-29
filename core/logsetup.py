from __future__ import annotations

import faulthandler
import logging
import logging.handlers
import os
import sys
import threading
from contextlib import contextmanager
from typing import Iterator

LOG_FORMAT = (
    "%(asctime)s.%(msecs)03d %(levelname)-7s [%(name)s]%(job)s %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "quickzip.log"
CRASH_FILE_NAME = "crash.log"
LOG_FILE_BYTES = 2 << 20
LOG_FILE_BACKUPS = 2
DEFAULT_LEVEL = "INFO"

log = logging.getLogger("quickzip.log")

_context = threading.local()
_state: dict[str, object] = {"configured": False, "crash_file": None}


class _JobFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        job = getattr(_context, "job", None)
        record.job = f" [{job}]" if job else ""
        return True


@contextmanager
def job_context(job_id: str | None) -> Iterator[None]:
    previous = getattr(_context, "job", None)
    _context.job = job_id
    try:
        yield
    finally:
        _context.job = previous


def log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "QuickZip", "logs")


def resolve_level(value: str | None) -> tuple[int, str | None]:
    name = (value or DEFAULT_LEVEL).strip().upper()
    level = logging.getLevelNamesMapping().get(name)
    if isinstance(level, int):
        return level, None
    return logging.INFO, name


def setup_logging(directory: str | None = None) -> str | None:
    if _state["configured"]:
        return _state.get("path")  # type: ignore[return-value]
    level, bad_level = resolve_level(os.environ.get("LOG_LEVEL"))
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    job_filter = _JobFilter()
    root = logging.getLogger()
    root.setLevel(level)

    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        console.addFilter(job_filter)
        root.addHandler(console)

    directory = directory or log_dir()
    path: str | None = os.path.join(directory, LOG_FILE_NAME)
    file_error: OSError | None = None
    try:
        os.makedirs(directory, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=LOG_FILE_BYTES, backupCount=LOG_FILE_BACKUPS,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        handler.addFilter(job_filter)
        root.addHandler(handler)
    except OSError as exc:
        file_error = exc
        path = None

    _state["configured"] = True
    _state["path"] = path
    if bad_level:
        log.warning("Unknown LOG_LEVEL=%r, using %s", bad_level, DEFAULT_LEVEL)
    if file_error is not None:
        log.warning(
            "File logging disabled: cannot open %s: %s",
            os.path.join(directory, LOG_FILE_NAME), file_error,
        )
    _enable_crash_dumps(directory)
    install_exception_hooks()
    return path


def _enable_crash_dumps(directory: str) -> None:
    crash_path = os.path.join(directory, CRASH_FILE_NAME)
    try:
        crash_file = open(crash_path, "a", encoding="utf-8")
        faulthandler.enable(file=crash_file, all_threads=True)
    except (OSError, ValueError, RuntimeError) as exc:
        log.warning("Crash dumps disabled: cannot use %s: %s", crash_path, exc)
        return
    _state["crash_file"] = crash_file
    log.debug("Fatal crash dumps go to %s", crash_path)


def install_exception_hooks() -> None:
    crash_log = logging.getLogger("quickzip.crash")

    def excepthook(exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        crash_log.critical(
            "Unhandled exception %s: %s", exc_type.__name__, exc,
            exc_info=(exc_type, exc, tb),
        )

    def thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        name = args.thread.name if args.thread is not None else "?"
        crash_log.critical(
            "Unhandled exception in thread %s: %s: %s",
            name, args.exc_type.__name__, args.exc_value,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    def unraisable_hook(unraisable) -> None:
        crash_log.error(
            "Unraisable exception (%s) in %r: %s",
            unraisable.err_msg or "ignored", unraisable.object,
            unraisable.exc_value,
            exc_info=(
                unraisable.exc_type, unraisable.exc_value,
                unraisable.exc_traceback,
            ),
        )

    sys.excepthook = excepthook
    threading.excepthook = thread_excepthook
    sys.unraisablehook = unraisable_hook
