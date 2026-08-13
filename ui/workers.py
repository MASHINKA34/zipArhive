from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from core.packer import ArchiveItem, PackOptions, PackResult, create_zip
from core.scanner import Node, ScanCancelled, scan_file, scan_tree


class ScanWorker(QThread):
    scanned = pyqtSignal(object)
    progress = pyqtSignal(int, int)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, path: str, as_file: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._path = path
        self._as_file = as_file
        self._stop = False

    @property
    def path(self) -> str:
        return self._path

    def cancel(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            if self._as_file:
                node: Node | None = scan_file(self._path)
            else:
                node = scan_tree(
                    self._path,
                    on_progress=self.progress.emit,
                    should_cancel=lambda: self._stop,
                )
        except ScanCancelled:
            self.cancelled.emit()
            return
        except OSError as error:
            self.failed.emit(str(error))
            return
        if node is None:
            self.failed.emit("Не удалось прочитать путь")
            return
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
    ) -> None:
        super().__init__(parent)
        self._zip_path = zip_path
        self._items = items
        self._options = options
        self._stop = False

    @property
    def zip_path(self) -> str:
        return self._zip_path

    def cancel(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            result: PackResult = create_zip(
                self._zip_path,
                self._items,
                self._options,
                progress=self.progress.emit,
                should_cancel=lambda: self._stop,
            )
        except OSError as error:
            self.failed.emit(str(error))
            return
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")
            return
        self.packed.emit(result)
