from __future__ import annotations

import logging
import sys
import threading
import time
import traceback

from PyQt6.QtCore import QObject, QTimer

log = logging.getLogger("quickzip.watchdog")


class StallWatchdog(QObject):
    def __init__(
        self,
        threshold: float = 3.0,
        beat_ms: int = 250,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._threshold = threshold
        self._beat_ms = beat_ms
        self._beat = time.monotonic()
        self._reported = False
        self._main_id = threading.get_ident()
        self._stop = threading.Event()
        self._timer = QTimer(self)
        self._timer.setInterval(beat_ms)
        self._timer.timeout.connect(self._on_beat)
        self._thread = threading.Thread(
            target=self._watch, name="ui-watchdog", daemon=True
        )

    def start(self) -> None:
        self._beat = time.monotonic()
        self._timer.start()
        self._thread.start()
        log.info(
            "UI stall watchdog started: threshold=%.1fs beat=%dms",
            self._threshold, self._beat_ms,
        )

    def stop(self) -> None:
        self._stop.set()
        self._timer.stop()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        log.info("UI stall watchdog stopped")

    def _on_beat(self) -> None:
        now = time.monotonic()
        if self._reported:
            self._reported = False
            log.warning(
                "UI thread responsive again after %.1fs stall",
                now - self._beat,
            )
        self._beat = now

    def _watch(self) -> None:
        interval = min(0.5, self._threshold / 4)
        while not self._stop.wait(interval):
            gap = time.monotonic() - self._beat
            if gap < self._threshold or self._reported:
                continue
            self._reported = True
            frame = sys._current_frames().get(self._main_id)
            if frame is None:
                stack = "  <no Python frame on the main thread>"
            else:
                stack = "".join(traceback.format_stack(frame)).rstrip()
            log.warning(
                "UI thread not responding for %.1fs; main thread stack "
                "(innermost last, a bare exec() frame means time is spent "
                "inside Qt):\n%s",
                gap, stack,
            )
