from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QThread, pyqtSignal

from core.logsetup import job_context
from core.packer import ArchiveItem, PackOptions, PackResult, create_zip
from core.scanner import Node, ScanCancelled, scan_file, scan_tree

log = logging.getLogger("quickzip.worker")


class ScanWorker(QThread):
    scanned = pyqtSignal(object)
    progress = pyqtSignal(int, int)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        path: str,
        as_file: bool = False,
        parent=None,
        job_id: str = "scan",
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._as_file = as_file
        self._job_id = job_id
        self._stop = False

    @property
    def path(self) -> str:
        return self._path

    @property
    def job_id(self) -> str:
        return self._job_id

    def cancel(self) -> None:
        self._stop = True

    def _on_progress(self, files: int, total_bytes: int) -> None:
        log.debug("Scan progress: %d files, %d bytes", files, total_bytes)
        self.progress.emit(files, total_bytes)

    def run(self) -> None:
        with job_context(self._job_id):
            self._run()

    def _run(self) -> None:
        started = time.perf_counter()
        log.info("Scan started: path=%s as_file=%s", self._path,
                 self._as_file)
        try:
            if self._as_file:
                node: Node | None = scan_file(self._path)
            else:
                node = scan_tree(
                    self._path,
                    on_progress=self._on_progress,
                    should_cancel=lambda: self._stop,
                )
        except ScanCancelled:
            self.cancelled.emit()
            return
        except OSError as error:
            log.error("Scan failed: path=%s: %s", self._path, error,
                      exc_info=True)
            self.failed.emit(str(error))
            return
        except Exception as error:
            log.exception("Scan crashed: path=%s", self._path)
            self.failed.emit(f"{type(error).__name__}: {error}")
            return
        if node is None:
            log.warning("Scan produced nothing: path is not readable: %s",
                        self._path)
            self.failed.emit("Не удалось прочитать путь")
            return
        log.info("Scan finished: %d files, %d bytes in %.0f ms", node.files,
                 node.size, (time.perf_counter() - started) * 1000)
        self.scanned.emit(node)


class PackWorker(QThread):
    progress = pyqtSignal(int, int, str)
    packed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        zip_path: str,
        items: list[ArchiveItem],
        options: PackOptions,
        parent=None,
        job_id: str = "pack",
    ) -> None:
        super().__init__(parent)
        self._zip_path = zip_path
        self._items = items
        self._options = options
        self._job_id = job_id
        self._stop = False

    @property
    def zip_path(self) -> str:
        return self._zip_path

    @property
    def job_id(self) -> str:
        return self._job_id

    def cancel(self) -> None:
        self._stop = True

    def run(self) -> None:
        with job_context(self._job_id):
            self._run()

    def _run(self) -> None:
        try:
            result: PackResult = create_zip(
                self._zip_path,
                self._items,
                self._options,
                progress=self.progress.emit,
                should_cancel=lambda: self._stop,
            )
        except OSError as error:
            log.error("Pack failed: target=%s: %s", self._zip_path, error,
                      exc_info=True)
            self.failed.emit(str(error))
            return
        except Exception as error:
            log.exception("Pack crashed: target=%s", self._zip_path)
            self.failed.emit(f"{type(error).__name__}: {error}")
            return
        self.packed.emit(result)
