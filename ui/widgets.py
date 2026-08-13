from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.formatting import human_size, plural_files
from ui.icons import app_icon, svg_icon, svg_pixmap
from ui.theme import (
    CANCEL_BUTTON_QSS,
    COMBO_QSS,
    C_ACCENT,
    C_ACCENT_HI,
    C_AMBER,
    C_BAR,
    C_BORDER,
    C_CLOSE,
    C_GREEN,
    C_PANEL,
    C_PANEL_ALT,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_FAINT,
    C_WINDOW,
    MUTED_BUTTON_QSS,
    PRIMARY_BUTTON_QSS,
    PROGRESS_QSS,
    TOOLBAR_QSS,
    TOOL_BUTTON_QSS,
)

MIXED = "mixed"


class TriCheckBox(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state: object = False
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Выделить всё")

    def state(self) -> object:
        return self._state

    def set_state(self, value: object) -> None:
        if self._state != value:
            self._state = value
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            new_state = self._state is not True
            self._state = new_state
            self.update()
            self.toggled.emit(new_state)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = self._state is True or self._state == MIXED
        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 1, 18, 18), 3, 3)
        if active:
            painter.fillPath(path, QColor(C_ACCENT))
            painter.setPen(QPen(QColor(C_ACCENT), 1))
        else:
            painter.fillPath(path, QColor(C_WINDOW))
            painter.setPen(QPen(QColor("#555555"), 1.5))
        painter.drawPath(path)

        if self._state is True:
            pen = QPen(QColor("white"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF([
                QPointF(5, 10), QPointF(8, 13), QPointF(15, 6),
            ]))
        elif self._state == MIXED:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("white"))
            painter.drawRoundedRect(QRectF(5, 9, 10, 2), 1, 1)
        painter.end()


class ToolbarButton(QPushButton):
    def __init__(self, icon_name: str, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setIcon(svg_icon(icon_name, 16, C_ACCENT_HI))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(TOOL_BUTTON_QSS)


class CaptionButton(QPushButton):
    def __init__(self, glyph: str, close: bool = False, parent=None) -> None:
        super().__init__(glyph, parent)
        self.setFixedSize(46, 32)
        hover = C_CLOSE if close else "#3a3a3a"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; border: none;
                color: {C_TEXT_DIM}; font-size: 11px;
                font-family: 'Segoe UI Symbol';
            }}
            QPushButton:hover {{ background: {hover}; color: white; }}
            """
        )


class TitleBar(QWidget):
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()
    move_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setObjectName("titlebar")
        self.setStyleSheet(
            f"#titlebar {{ background: {C_BAR}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        glyph = QLabel()
        glyph.setFixedSize(18, 18)
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setPixmap(app_icon().pixmap(QSize(18, 18)))
        layout.addWidget(glyph)

        title = QLabel("Quick Zip")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        layout.addWidget(title)
        layout.addStretch(1)

        buttons = (
            (CaptionButton("—"), self.minimize_requested),
            (CaptionButton("□"), self.maximize_requested),
            (CaptionButton("✕", close=True), self.close_requested),
        )
        for button, signal in buttons:
            button.clicked.connect(signal.emit)
            layout.addWidget(button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.move_requested.emit()

    def mouseDoubleClickEvent(self, _event) -> None:
        self.maximize_requested.emit()


class EmptyState(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"EmptyState {{ background: {C_WINDOW}; }}")
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._zone = QFrame()
        self._zone.setObjectName("zone")
        self._zone.setFixedWidth(440)
        zone_layout = QVBoxLayout(self._zone)
        zone_layout.setContentsMargins(32, 44, 32, 44)
        zone_layout.setSpacing(18)
        zone_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel()
        badge.setFixedSize(80, 80)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background: rgba(0,120,212,0.12); border-radius: 16px;"
        )
        badge.setPixmap(svg_pixmap("box", 44, C_ACCENT_HI))
        zone_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Перетащите папку сюда")
        title.setStyleSheet(
            f"color: {C_TEXT}; font-size: 16px; font-weight: 600;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(title)

        subtitle = QLabel(
            'или нажмите <span style="color:#3A9BE5;font-weight:600;">'
            "Добавить папку</span>, чтобы начать"
        )
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        subtitle.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(subtitle)

        hint = QLabel("Папки можно раскрывать и отмечать файлы галочками")
        hint.setStyleSheet(
            f"color: {C_TEXT_FAINT}; font-size: 11px; "
            f"border-top: 1px solid {C_PANEL_ALT}; padding-top: 10px;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(hint)

        outer.addWidget(self._zone)
        self.set_highlighted(False)

    def set_highlighted(self, active: bool) -> None:
        color = C_ACCENT_HI if active else "#3a4a5e"
        background = "#1f2a36" if active else C_BAR
        self._zone.setStyleSheet(
            f"#zone {{ border: 2px dashed {color}; border-radius: 8px; "
            f"background: {background}; }}"
        )


class Toolbar(QWidget):
    add_folder_requested = pyqtSignal()
    add_files_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    level_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbar")
        self.setStyleSheet(TOOLBAR_QSS)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.add_folder_button = ToolbarButton("add_folder", "Добавить папку")
        self.add_folder_button.clicked.connect(
            self.add_folder_requested.emit
        )
        self.add_files_button = ToolbarButton("add_file", "Добавить файлы")
        self.add_files_button.clicked.connect(self.add_files_requested.emit)
        self.clear_button = ToolbarButton("clear", "Очистить всё")
        self.clear_button.clicked.connect(self.clear_requested.emit)

        separator = QFrame()
        separator.setFixedSize(1, 22)
        separator.setStyleSheet(f"background: {C_BORDER};")

        layout.addWidget(self.add_folder_button)
        layout.addWidget(self.add_files_button)
        layout.addSpacing(4)
        layout.addWidget(separator)
        layout.addSpacing(4)
        layout.addWidget(self.clear_button)
        layout.addStretch(1)

        label = QLabel("Сжатие")
        label.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px;")
        layout.addWidget(label)

        self.level_box = QComboBox()
        self.level_box.setStyleSheet(COMBO_QSS)
        self.level_box.setCursor(Qt.CursorShape.PointingHandCursor)
        self.level_box.addItem("Быстрое", 1)
        self.level_box.addItem("Обычное", 6)
        self.level_box.addItem("Максимальное", 9)
        self.level_box.setCurrentIndex(1)
        self.level_box.currentIndexChanged.connect(
            lambda _index: self.level_changed.emit(self.level())
        )
        layout.addWidget(self.level_box)

    def level(self) -> int:
        return int(self.level_box.currentData())

    def set_level(self, level: int) -> None:
        index = self.level_box.findData(level)
        if index >= 0:
            self.level_box.setCurrentIndex(index)

    def set_busy(self, busy: bool) -> None:
        for widget in (
            self.add_folder_button, self.add_files_button,
            self.clear_button, self.level_box,
        ):
            widget.setEnabled(not busy)


class BottomPanel(QWidget):
    pack_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    SPEED_BY_LEVEL = {1: 340.0, 6: 230.0, 9: 85.0}
    RATIO_BY_LEVEL = {1: 0.72, 6: 0.62, 9: 0.58}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("bottom")
        self.setStyleSheet(
            f"#bottom {{ background: {C_PANEL}; "
            f"border-top: 1px solid {C_BORDER}; }}"
        )
        self._level = 6
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        self.summary = QLabel()
        self.summary.setStyleSheet(f"font-size: 13px; color: {C_TEXT};")
        self.estimate = QLabel()
        self.estimate.setStyleSheet(f"font-size: 11px; color: {C_TEXT_FAINT};")
        self.progress = QProgressBar()
        self.progress.setStyleSheet(PROGRESS_QSS)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setRange(0, 1000)
        self.progress.hide()
        left.addWidget(self.summary)
        left.addWidget(self.estimate)
        left.addWidget(self.progress)
        layout.addLayout(left, 1)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.setStyleSheet(CANCEL_BUTTON_QSS)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)

        self.pack_button = QPushButton("Упаковать в ZIP")
        self.pack_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pack_button.setIcon(svg_icon("chevron", 14, "white"))
        self.pack_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.pack_button.clicked.connect(self.pack_requested.emit)
        layout.addWidget(self.pack_button)
        self.set_summary(0, 0)

    def set_level(self, level: int) -> None:
        self._level = level

    def set_summary(self, count: int, total_bytes: int) -> None:
        enabled = count > 0
        self.pack_button.setEnabled(enabled)
        self.pack_button.setStyleSheet(
            PRIMARY_BUTTON_QSS if enabled else MUTED_BUTTON_QSS
        )
        if not enabled:
            self.summary.setText(
                f'<span style="color:{C_TEXT_DIM};">Выбрано: </span><b>0</b>'
                f'<span style="color:{C_TEXT_DIM};"> файлов</span>'
            )
            self.estimate.setText("Добавьте папку, чтобы начать")
            return
        self.summary.setText(
            f'<span style="color:{C_TEXT_DIM};">Выбрано: </span>'
            f"<b>{count}</b>"
            f'<span style="color:{C_TEXT_DIM};"> {plural_files(count)} '
            f"({human_size(total_bytes)})</span>"
        )
        ratio = self.RATIO_BY_LEVEL.get(self._level, 0.62)
        speed = self.SPEED_BY_LEVEL.get(self._level, 230.0) * (1 << 20)
        seconds = max(1, round(total_bytes / speed))
        self.estimate.setText(
            f"≈ {human_size(int(total_bytes * ratio))} после сжатия · "
            f"~{seconds} с"
        )

    def set_scanning(self, files: int, total_bytes: int) -> None:
        self.summary.setText(
            f'<span style="color:{C_TEXT_DIM};">Сканирование… </span>'
            f"<b>{files}</b>"
            f'<span style="color:{C_TEXT_DIM};"> {plural_files(files)} '
            f"({human_size(total_bytes)})</span>"
        )
        self.estimate.setText("Читаю содержимое папки")

    def start_progress(self) -> None:
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.show()
        self.pack_button.hide()

    def stop_progress(self) -> None:
        self.progress.hide()
        self.cancel_button.hide()
        self.pack_button.show()

    def set_progress(self, done: int, total: int, text: str) -> None:
        value = int(done * 1000 / total) if total else 0
        self.progress.setValue(min(1000, max(0, value)))
        percent = f"{value / 10:.1f}".replace(".", ",")
        self.summary.setText(
            f'<span style="color:{C_TEXT_DIM};">Упаковка… </span>'
            f"<b>{percent}%</b>"
        )
        self.estimate.setText(text)


class StatusBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setObjectName("status")
        self.setStyleSheet(
            f"#status {{ background: {C_BAR}; "
            f"border-top: 1px solid {C_BORDER}; }}"
            f"QLabel {{ color: {C_TEXT_DIM}; font-size: 11px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._dot = QLabel()
        self._dot.setFixedSize(6, 6)
        layout.addWidget(self._dot)
        self.left = QLabel("Готово")
        layout.addWidget(self.left)
        layout.addStretch(1)
        self.right = QLabel("0 элементов")
        layout.addWidget(self.right)
        self.set_busy(False)

    def set_busy(self, busy: bool) -> None:
        color = C_AMBER if busy else C_GREEN
        self._dot.setStyleSheet(f"background: {color}; border-radius: 3px;")

    def set_text(self, left: str, right: str | None = None) -> None:
        self.left.setText(left)
        if right is not None:
            self.right.setText(right)
