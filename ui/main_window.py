from __future__ import annotations

import os
import sys
import time
from collections import deque

from PyQt6.QtCore import (
    QLibraryInfo,
    QLocale,
    QPoint,
    QProcess,
    QSettings,
    QSize,
    Qt,
    QTimer,
    QTranslator,
)
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHeaderView,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from core.formatting import (
    human_duration,
    human_size,
    human_speed,
    plural_files,
    plural_items,
)
from core.packer import PackOptions, PackResult, default_workers
from core.scanner import Node, collect_items, summary
from ui.file_model import FileTreeModel
from ui.icons import app_icon
from ui.style import TreeStyle
from ui.theme import APP_QSS, C_WINDOW, MENU_QSS, TREE_QSS, dark_palette
from ui.widgets import (
    MIXED,
    BottomPanel,
    EmptyState,
    StatusBar,
    TitleBar,
    Toolbar,
    TriCheckBox,
)
from ui.workers import PackWorker, ScanWorker

APP_NAME = "Quick Zip"
APP_VERSION = "1.2.0"
RESIZE_MARGIN = 5
IDLE, SCANNING, PACKING = 0, 1, 2


class MainWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(800, 600)
        self.resize(1040, 700)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setObjectName("root")
        self.setStyleSheet(f"#root {{ background: {C_WINDOW}; }}")

        self._settings = QSettings("QuickZip", "QuickZip")
        self._state = IDLE
        self._scan_queue: deque[tuple[str, bool]] = deque()
        self._scanner: ScanWorker | None = None
        self._packer: PackWorker | None = None
        self._suggested_name = ""
        self._suggested_dir = ""
        self._target_name = "архив.zip"
        self._pack_started = 0.0
        self._closing = False
        self._note = ""
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.timeout.connect(self._clear_note)

        self.model = FileTreeModel(self)
        self.model.selection_changed.connect(self._refresh_summary)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN
        )
        layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self.toggle_max_restore)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.move_requested.connect(self._start_move)
        layout.addWidget(self.title_bar)

        self.toolbar = Toolbar(self)
        self.toolbar.add_folder_requested.connect(self._choose_folder)
        self.toolbar.add_files_requested.connect(self._choose_files)
        self.toolbar.clear_requested.connect(self._clear_all)
        self.toolbar.level_changed.connect(self._on_level_changed)
        layout.addWidget(self.toolbar)

        self.stack = QStackedWidget()
        self.empty = EmptyState()
        self.view = self._build_view()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.view)
        layout.addWidget(self.stack, 1)

        self.bottom = BottomPanel()
        self.bottom.pack_requested.connect(self._start_pack)
        self.bottom.cancel_requested.connect(self._cancel_current)
        layout.addWidget(self.bottom)

        self.status = StatusBar()
        layout.addWidget(self.status)

        self._restore_settings()
        self._install_shortcuts()
        self._refresh_summary()

    def _build_view(self) -> QTreeView:
        view = QTreeView()
        view.setModel(self.model)
        self._tree_style = TreeStyle()
        self._tree_style.setParent(view)
        view.setStyle(self._tree_style)
        view.setStyleSheet(TREE_QSS)
        view.setUniformRowHeights(True)
        view.setAlternatingRowColors(True)
        view.setIndentation(16)
        view.setIconSize(QSize(22, 22))
        view.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setExpandsOnDoubleClick(True)
        view.setAllColumnsShowFocus(True)
        view.setSortingEnabled(False)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(self._show_context_menu)
        view.expanded.connect(
            lambda index: self.model.set_expanded(index, True)
        )
        view.collapsed.connect(
            lambda index: self.model.set_expanded(index, False)
        )

        header = view.header()
        header.setFixedHeight(38)
        header.setStretchLastSection(False)
        header.setSortIndicatorShown(False)
        header.setSectionsClickable(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        view.setColumnWidth(1, 110)
        view.setColumnWidth(2, 300)

        self.select_all_box = TriCheckBox(header)
        self.select_all_box.setGeometry(15, 9, 20, 20)
        self.select_all_box.toggled.connect(self.model.set_all_checked)
        self.select_all_box.raise_()
        return view

    def _install_shortcuts(self) -> None:
        bindings = (
            ("Ctrl+O", self._choose_folder),
            ("Ctrl+Shift+O", self._choose_files),
            ("Ctrl+Shift+Delete", self._clear_all),
            ("Ctrl+Return", self._start_pack),
            ("Ctrl+A", lambda: self.model.set_all_checked(True)),
            ("Ctrl+D", lambda: self.model.set_all_checked(False)),
            ("Delete", self._remove_selected),
            ("F5", self._rescan_roots),
            ("Escape", self._cancel_current),
        )
        for key, handler in bindings:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(handler)

    def _restore_settings(self) -> None:
        geometry = self._settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        level = self._settings.value("pack/level", 6, type=int)
        self.toolbar.set_level(level)
        self.bottom.set_level(self.toolbar.level())
        self._suggested_dir = self._settings.value("pack/last_dir", "",
                                                   type=str)

    def _save_settings(self) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("pack/level", self.toolbar.level())
        self._settings.setValue("pack/last_dir", self._suggested_dir)

    def _on_level_changed(self, level: int) -> None:
        self.bottom.set_level(level)
        self._refresh_summary()

    def add_path(self, path: str) -> None:
        path = os.path.normpath(path)
        if os.path.isdir(path):
            self._scan_queue.append((path, False))
        elif os.path.isfile(path):
            self._scan_queue.append((path, True))
        else:
            return
        self._start_next_scan()

    def _choose_folder(self) -> None:
        if self._state != IDLE:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку", self._suggested_dir
        )
        if folder:
            self.add_path(folder)

    def _choose_files(self) -> None:
        if self._state != IDLE:
            return
        paths, _filter = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", self._suggested_dir
        )
        for path in paths:
            self.add_path(path)

    def _start_next_scan(self) -> None:
        if self._scanner is not None or not self._scan_queue:
            return
        path, as_file = self._scan_queue.popleft()
        worker = ScanWorker(path, as_file, self)
        worker.scanned.connect(self._on_scanned)
        worker.progress.connect(self.bottom.set_scanning)
        worker.failed.connect(self._on_scan_failed)
        worker.cancelled.connect(self._on_scan_cancelled)
        worker.finished.connect(self._on_scan_finished)
        self._scanner = worker
        self._set_state(SCANNING)
        self.status.set_text(f"Сканирование «{os.path.basename(path)}»…")
        worker.start()

    def _on_scanned(self, node: Node) -> None:
        existing = self.model.find_root(node.root_path)
        if existing >= 0:
            self.model.remove_root(existing)
        index = self.model.add_root(node)
        if node.is_dir:
            self.view.expand(index)
            self._suggested_name = node.name or "архив"
            self._suggested_dir = os.path.dirname(node.root_path)
        elif not self._suggested_dir:
            self._suggested_dir = os.path.dirname(node.root_path)
        if not self._suggested_name:
            self._suggested_name = node.name or "архив"
        self._set_note(f"Добавлено: «{node.name}»")

    def _on_scan_failed(self, message: str) -> None:
        self._set_note(f"Ошибка чтения: {message}")

    def _on_scan_cancelled(self) -> None:
        self._scan_queue.clear()
        self._set_note("Сканирование отменено")

    def _on_scan_finished(self) -> None:
        self._scanner = None
        if self._scan_queue:
            self._start_next_scan()
            return
        self._set_state(IDLE)
        self._refresh_summary()

    def _rescan_roots(self) -> None:
        if self._state != IDLE or self.model.is_empty():
            return
        paths = [
            (node.root_path, not node.is_dir) for node in self.model.roots
        ]
        self.model.clear()
        self._scan_queue.extend(paths)
        self._start_next_scan()

    def _clear_all(self) -> None:
        if self._state != IDLE:
            return
        self.model.clear()
        self._suggested_name = ""
        self._refresh_summary()
        self._set_note("Список очищен")

    def _remove_selected(self) -> None:
        if self._state != IDLE:
            return
        indexes = [
            index for index in self.view.selectionModel().selectedRows()
            if index.isValid()
        ]
        if not indexes:
            return
        self.model.remove_indexes(indexes)
        self._refresh_summary()

    def _show_context_menu(self, position: QPoint) -> None:
        index = self.view.indexAt(position)
        menu = QMenu(self)
        menu.setStyleSheet(MENU_QSS)
        if index.isValid():
            node = self.model.node_at(index)
            open_action = QAction("Показать в проводнике", menu)
            open_action.triggered.connect(lambda: self._reveal(node.path))
            menu.addAction(open_action)
            remove_action = QAction("Убрать из списка", menu)
            remove_action.triggered.connect(self._remove_selected)
            menu.addAction(remove_action)
            menu.addSeparator()
        expand_action = QAction("Развернуть всё", menu)
        expand_action.triggered.connect(self.view.expandAll)
        menu.addAction(expand_action)
        collapse_action = QAction("Свернуть всё", menu)
        collapse_action.triggered.connect(self.view.collapseAll)
        menu.addAction(collapse_action)
        menu.addSeparator()
        clear_action = QAction("Очистить всё", menu)
        clear_action.triggered.connect(self._clear_all)
        menu.addAction(clear_action)
        menu.exec(self.view.viewport().mapToGlobal(position))

    def _reveal(self, path: str) -> None:
        if sys.platform == "win32":
            QProcess.startDetached("explorer.exe", ["/select,", path])
        else:
            QProcess.startDetached("xdg-open", [os.path.dirname(path)])

    def _refresh_summary(self) -> None:
        roots = self.model.roots
        has_items = bool(roots)
        self.stack.setCurrentIndex(1 if has_items else 0)
        files, checked_files, _size, checked_size = summary(roots)
        if self._state != PACKING:
            self.bottom.set_summary(checked_files, checked_size)
        if checked_files == 0:
            self.select_all_box.set_state(False)
        elif checked_files == files:
            self.select_all_box.set_state(True)
        else:
            self.select_all_box.set_state(MIXED)
        if self._state != IDLE or self._note:
            return
        if files:
            self.status.set_text(
                f"Загружено {files} {plural_files(files)} · "
                f"{checked_files} выбрано",
                self._target_name,
            )
        else:
            self.status.set_text("Готово", "0 элементов")

    def _set_note(self, text: str, timeout: int = 6000) -> None:
        self._note = text
        self.status.set_text(text, self._target_name)
        self._note_timer.start(timeout)

    def _clear_note(self) -> None:
        self._note = ""
        self._refresh_summary()

    def _set_state(self, state: int) -> None:
        self._state = state
        busy = state != IDLE
        self.toolbar.set_busy(busy)
        self.status.set_busy(busy)
        if state == PACKING:
            self.bottom.start_progress()
        else:
            self.bottom.stop_progress()
        if state == SCANNING:
            self.bottom.cancel_button.show()
            self.bottom.pack_button.hide()
        elif state == IDLE:
            self.bottom.cancel_button.hide()
            self.bottom.pack_button.show()

    def _start_pack(self) -> None:
        if self._state != IDLE:
            return
        items = collect_items(self.model.roots)
        if not items:
            return
        base_name = self._suggested_name or "архив"
        init_dir = self._suggested_dir or os.path.expanduser("~")
        target, _filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить архив",
            os.path.join(init_dir, base_name + ".zip"),
            "ZIP-архив (*.zip)",
        )
        if not target:
            return
        if not target.lower().endswith(".zip"):
            target += ".zip"
        self._target_name = os.path.basename(target)
        self._suggested_dir = os.path.dirname(target)

        options = PackOptions(
            level=self.toolbar.level(),
            smart_store=self.toolbar.level() < 9,
            workers=default_workers(),
        )
        worker = PackWorker(target, items, options, self)
        worker.progress.connect(self._on_pack_progress)
        worker.packed.connect(self._on_packed)
        worker.failed.connect(self._on_pack_failed)
        worker.finished.connect(self._on_pack_finished)
        self._packer = worker
        self._pack_started = time.monotonic()
        self._set_state(PACKING)
        self.status.set_text("Упаковка…", self._target_name)
        worker.start()

    def _on_pack_progress(self, done: int, total: int, name: str) -> None:
        elapsed = max(time.monotonic() - self._pack_started, 0.001)
        speed = done / elapsed
        remaining = (total - done) / speed if speed > 0 else 0.0
        details = f"{human_size(done)} из {human_size(total)}"
        if speed > 0:
            details += (
                f" · {human_speed(speed)} · осталось "
                f"{human_duration(remaining)}"
            )
        self.bottom.set_progress(done, total, details)
        if name:
            self.status.set_text(f"Упаковка… {name}", self._target_name)

    def _on_packed(self, result: PackResult) -> None:
        if result.cancelled:
            self._set_note("Упаковка отменена")
            return
        target = self._packer.zip_path if self._packer else ""
        saved = 1.0 - result.ratio
        self._set_note(
            f"Готово · {result.written} "
            f"{plural_items(result.written)} за "
            f"{human_duration(result.elapsed)}",
            20000,
        )
        if self._closing:
            return
        text = (
            f"Архив создан:\n{target}\n\n"
            f"Записано: {result.written} {plural_items(result.written)}\n"
            f"Размер архива: {human_size(result.archive_size)} "
            f"(экономия {saved * 100:.0f}%)\n"
            f"Время: {human_duration(result.elapsed)} · "
            f"{human_speed(result.total_size / max(result.elapsed, 0.001))}"
        )
        if result.skipped:
            text += f"\nПропущено файлов: {result.skipped}"
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(text)
        if result.warnings:
            box.setDetailedText("\n".join(result.warnings[:50]))
        reveal = box.addButton(
            "Показать в проводнике", QMessageBox.ButtonRole.AcceptRole
        )
        box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is reveal:
            self._reveal(target)

    def _on_pack_failed(self, message: str) -> None:
        self._set_note("Ошибка упаковки")
        if not self._closing:
            QMessageBox.critical(
                self, APP_NAME, f"Не удалось создать архив:\n{message}"
            )

    def _on_pack_finished(self) -> None:
        self._packer = None
        self._set_state(IDLE)
        self._refresh_summary()

    def _cancel_current(self) -> None:
        if self._state == SCANNING and self._scanner is not None:
            self._scanner.cancel()
        elif self._state == PACKING and self._packer is not None:
            self._packer.cancel()
            self.status.set_text("Отмена…", self._target_name)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and self._state != PACKING:
            event.acceptProposedAction()
            self.empty.set_highlighted(True)

    def dragLeaveEvent(self, _event) -> None:
        self.empty.set_highlighted(False)

    def dropEvent(self, event) -> None:
        self.empty.set_highlighted(False)
        if self._state == PACKING:
            return
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                self.add_path(local)
        event.acceptProposedAction()

    def toggle_max_restore(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _start_move(self) -> None:
        handle = self.windowHandle()
        if handle is not None:
            handle.startSystemMove()

    def _edges_at(self, position) -> Qt.Edge:
        if self.isMaximized():
            return Qt.Edge(0)
        rect = self.rect()
        margin = RESIZE_MARGIN + 2
        edges = Qt.Edge(0)
        if position.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        if position.x() >= rect.width() - margin:
            edges |= Qt.Edge.RightEdge
        if position.y() <= margin:
            edges |= Qt.Edge.TopEdge
        if position.y() >= rect.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for(edges: Qt.Edge) -> Qt.CursorShape:
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        if (left and top) or (right and bottom):
            return Qt.CursorShape.SizeFDiagCursor
        if (right and top) or (left and bottom):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mouseMoveEvent(self, event) -> None:
        self.setCursor(self._cursor_for(self._edges_at(
            event.position().toPoint()
        )))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._edges_at(event.position().toPoint())
            if edges != Qt.Edge(0):
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:
        self._closing = True
        self._save_settings()
        self._scan_queue.clear()
        for worker in (self._scanner, self._packer):
            if worker is not None and worker.isRunning():
                worker.cancel()
                worker.wait(5000)
        event.accept()


def _install_translator(application: QApplication) -> None:
    translator = QTranslator(application)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(QLocale.system(), "qtbase", "_", path):
        application.installTranslator(translator)


def run(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "QuickZip.Desktop.App"
            )
        except Exception:
            pass

    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName("QuickZip")
    application = QApplication(arguments)
    application.setStyle("Fusion")
    application.setPalette(dark_palette())
    application.setStyleSheet(APP_QSS)
    _install_translator(application)
    icon = app_icon()
    application.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    for path in arguments[1:]:
        if not path.startswith("-"):
            QTimer.singleShot(0, lambda item=path: window.add_path(item))
    return application.exec()
