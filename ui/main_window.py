from __future__ import annotations

import base64
import os
import sys
import tempfile

from PyQt6.QtCore import (
    QByteArray,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
    QTransform,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.archiver import (
    ArchiveItem,
    create_zip,
    human_size,
    plural_files,
)
from ui.appicon_data import APPICON_PNG_B64

C_CANVAS = "#0f0f0f"
C_WINDOW = "#1a1a1a"
C_BAR = "#202020"
C_PANEL = "#252525"
C_PANEL_ALT = "#2a2a2a"
C_BORDER = "#333333"
C_ACCENT = "#0078D4"
C_ACCENT_HI = "#3A9BE5"
C_ACCENT_BR = "#1A8AE0"
C_TEXT = "#ffffff"
C_TEXT_DIM = "#888888"
C_TEXT_SOFT = "#cccccc"
C_TEXT_FAINT = "#666666"
C_GREEN = "#2BC27A"
C_CLOSE = "#C42B1C"

_TYPE_MAP = {
    "jpg": ("#7B5EA7", "JPG"), "jpeg": ("#7B5EA7", "JPG"),
    "png": ("#6A8B5A", "PNG"), "gif": ("#6A8B5A", "GIF"),
    "bmp": ("#6A8B5A", "BMP"), "webp": ("#6A8B5A", "WEBP"),
    "svg": ("#6A8B5A", "SVG"), "heic": ("#6A8B5A", "HEIC"),
    "mp4": ("#C24A4A", "MP4"), "mov": ("#C24A4A", "MOV"),
    "avi": ("#C24A4A", "AVI"), "mkv": ("#C24A4A", "MKV"),
    "webm": ("#C24A4A", "WEBM"),
    "mp3": ("#2E8B8B", "MP3"), "wav": ("#2E8B8B", "WAV"),
    "flac": ("#2E8B8B", "FLAC"), "ogg": ("#2E8B8B", "OGG"),
    "docx": ("#2B5BA0", "DOCX"), "doc": ("#2B5BA0", "DOC"),
    "rtf": ("#2B5BA0", "RTF"),
    "pdf": ("#B83A3A", "PDF"),
    "xlsx": ("#1F7A4D", "XLSX"), "xls": ("#1F7A4D", "XLS"),
    "csv": ("#1F7A4D", "CSV"),
    "pptx": ("#C15D2E", "PPTX"), "ppt": ("#C15D2E", "PPT"),
    "txt": ("#5A6470", "TXT"), "log": ("#5A6470", "LOG"),
    "md": ("#5A6470", "MD"), "json": ("#5A6470", "JSON"),
    "xml": ("#5A6470", "XML"), "yml": ("#5A6470", "YML"),
    "yaml": ("#5A6470", "YAML"), "ini": ("#5A6470", "INI"),
    "py": ("#3B6EA5", "PY"), "js": ("#C9A227", "JS"),
    "ts": ("#2B7FBF", "TS"), "html": ("#C1502E", "HTML"),
    "css": ("#2B6FB8", "CSS"), "sh": ("#4F7A4F", "SH"),
    "sql": ("#8A6D3B", "SQL"),
    "zip": ("#C9952B", "ZIP"), "rar": ("#C9952B", "RAR"),
    "7z": ("#C9952B", "7Z"), "gz": ("#C9952B", "GZ"),
    "tar": ("#C9952B", "TAR"),
    "exe": ("#6B7280", "EXE"), "msi": ("#6B7280", "MSI"),
    "dll": ("#6B7280", "DLL"), "iso": ("#7A6CA8", "ISO"),
}

_SVG = {
    "add_folder": (
        '<svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M1.75 4.25C1.75 3.56 2.31 3 3 3h3.17c.33 0 .64.13.87.36l.85.85c.23.23.55.36.88.36H13c.69 0 1.25.56 1.25 1.25v6.43c0 .69-.56 1.25-1.25 1.25H3c-.69 0-1.25-.56-1.25-1.25V4.25Z" stroke="{c}" stroke-width="1.1" stroke-linejoin="round"/>'
        '<path d="M8 8V11.5M6.25 9.75H9.75" stroke="{c}" stroke-width="1.1" stroke-linecap="round"/></svg>'
    ),
    "clear": (
        '<svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M3 4.5h10M6.5 4.5V3a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.5M4.5 4.5l.6 8.1A1 1 0 0 0 6.1 13.5h3.8a1 1 0 0 0 1-.9l.6-8.1" stroke="{c}" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "box": (
        '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M32 8L54 18V44L32 56L10 44V18L32 8Z" stroke="{c}" stroke-width="1.5" stroke-linejoin="round"/>'
        '<path d="M10 18L32 28L54 18M32 28V56" stroke="{c}" stroke-width="1.5" stroke-linejoin="round"/>'
        '<path d="M21 13L43 23" stroke="{c}" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="2 2"/></svg>'
    ),
    "chevron": (
        '<svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M6 4L10 8L6 12" stroke="{c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
}

_tile_cache: dict[str, QIcon] = {}
_folder_icon_cache: list[QIcon] = []
_icon_provider: list[QFileIconProvider] = []
_arrow_cache: list[tuple[str, str]] = []


def asset_path(*parts: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        root = sys._MEIPASS
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, *parts)


def _dpr() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def svg_icon(name: str, size: int, color: str) -> QPixmap:
    ratio = _dpr()
    px = max(1, int(size * ratio))
    data = QByteArray(_SVG[name].format(c=color).encode("utf-8"))
    renderer = QSvgRenderer(data)
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def kind_of(path: str) -> str:
    return os.path.splitext(path)[1].lstrip(".").lower()


def file_tile(ext: str, size: int = 22) -> QPixmap:
    info = _TYPE_MAP.get(ext)
    if info:
        color, label = info
    elif ext:
        color, label = "#5A6470", ext.upper()[:4]
    else:
        color, label = "#5A6470", ""

    ratio = _dpr()
    px = int(size * ratio)
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(ratio, ratio)

    base = QColor(color)
    rect = QRectF(0.5, 0.5, size - 1, size - 1)
    body = QPainterPath()
    body.addRoundedRect(rect, 5, 5)
    p.fillPath(body, base)

    fold = 7
    tri = QPolygonF([
        QPointF(size - fold, 0.5),
        QPointF(size - 0.5, 0.5),
        QPointF(size - 0.5, fold),
    ])
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(base.darker(140))
    p.drawPolygon(tri)
    p.setPen(QPen(base.lighter(118), 1))
    p.drawLine(QPointF(size - fold, 0.5), QPointF(size - fold, fold))
    p.drawLine(QPointF(size - fold, fold), QPointF(size - 0.5, fold))

    if label:
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(8 if len(label) <= 3 else 6)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(0, 1, size, size - 1),
                   Qt.AlignmentFlag.AlignCenter, label)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 215))
        line_w = size * 0.5
        x = (size - line_w) / 2
        for i, y in enumerate((size * 0.34, size * 0.5, size * 0.66)):
            w = line_w if i < 2 else line_w * 0.6
            p.drawRoundedRect(QRectF(x, y, w, 1.8), 1, 1)

    p.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def tile_icon(path: str) -> QIcon:
    ext = kind_of(path)
    key = ext or "_"
    icon = _tile_cache.get(key)
    if icon is None:
        icon = QIcon(file_tile(ext))
        _tile_cache[key] = icon
    return icon


def folder_icon() -> QIcon:
    if not _folder_icon_cache:
        if not _icon_provider:
            _icon_provider.append(QFileIconProvider())
        _folder_icon_cache.append(
            _icon_provider[0].icon(QFileIconProvider.IconType.Folder)
        )
    return _folder_icon_cache[0]


def app_icon() -> QIcon:
    ico = asset_path("assets", "icons", "app.ico")
    if os.path.exists(ico):
        disk = QIcon(ico)
        if not disk.isNull() and disk.availableSizes():
            return disk
    pm = QPixmap()
    pm.loadFromData(base64.b64decode(APPICON_PNG_B64), "PNG")
    icon = QIcon()
    for s in (16, 20, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(
            pm.scaled(
                s, s,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    return icon


def branch_arrows() -> tuple[str, str]:
    if _arrow_cache:
        return _arrow_cache[0]
    folder = os.path.join(tempfile.gettempdir(), "quickzip_ui")
    os.makedirs(folder, exist_ok=True)
    closed_path = os.path.join(folder, "arrow_closed.png")
    open_path = os.path.join(folder, "arrow_open.png")
    right = svg_icon("chevron", 13, "#c8c8c8")
    right.save(closed_path, "PNG")
    down = right.transformed(
        QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation
    )
    down.save(open_path, "PNG")
    result = (
        closed_path.replace(os.sep, "/"),
        open_path.replace(os.sep, "/"),
    )
    _arrow_cache.append(result)
    return result


class TriCheckBox(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = False
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def state(self):
        return self._state

    def set_state(self, value):
        if self._state != value:
            self._state = value
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            new = not (self._state is True)
            self._state = new
            self.update()
            self.toggled.emit(new)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = self._state is True or self._state == "mixed"
        rect = QRectF(1, 1, 18, 18)
        path = QPainterPath()
        path.addRoundedRect(rect, 3, 3)
        if active:
            p.fillPath(path, QColor(C_ACCENT))
            p.setPen(QPen(QColor(C_ACCENT), 1))
        else:
            p.fillPath(path, QColor(C_WINDOW))
            p.setPen(QPen(QColor("#555555"), 1.5))
        p.drawPath(path)

        if self._state is True:
            pen = QPen(QColor("white"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            poly = QPolygonF([
                QPointF(5, 10), QPointF(8, 13), QPointF(15, 6),
            ])
            p.drawPolyline(poly)
        elif self._state == "mixed":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("white"))
            p.drawRoundedRect(QRectF(5, 9, 10, 2), 1, 1)
        p.end()


class ToolbarButton(QPushButton):
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(text, parent)
        self.setIcon(QIcon(svg_icon(icon_name, 16, C_ACCENT_HI)))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {C_PANEL_ALT};
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                padding: 7px 14px;
                color: {C_TEXT};
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{ background: #323232; }}
            QPushButton:pressed {{ background: #2f2f2f; }}
            """
        )


class CaptionButton(QPushButton):
    def __init__(self, glyph: str, close=False, parent=None):
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
    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._win = window
        self.setFixedHeight(32)
        self.setObjectName("titlebar")
        self.setStyleSheet(
            f"#titlebar {{ background: {C_BAR}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(8)

        glyph = QLabel()
        glyph.setFixedSize(18, 18)
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setPixmap(
            app_icon().pixmap(QSize(18, 18))
        )
        lay.addWidget(glyph)

        title = QLabel("Quick Zip")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        lay.addWidget(title)
        lay.addStretch(1)

        self._btn_min = CaptionButton("—")
        self._btn_max = CaptionButton("□")
        self._btn_close = CaptionButton("✕", close=True)
        self._btn_min.clicked.connect(window.showMinimized)
        self._btn_max.clicked.connect(window.toggle_max_restore)
        self._btn_close.clicked.connect(window.close)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            lay.addWidget(b)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._win.windowHandle()
            if handle is not None:
                handle.startSystemMove()

    def mouseDoubleClickEvent(self, _event):
        self._win.toggle_max_restore()


class EmptyState(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"EmptyState {{ background: {C_WINDOW}; }}")
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        zone = QFrame()
        zone.setObjectName("zone")
        zone.setFixedWidth(440)
        zone.setStyleSheet(
            "#zone { border: 2px dashed #3a4a5e; border-radius: 8px; "
            f"background: {C_BAR}; }}"
        )
        zlay = QVBoxLayout(zone)
        zlay.setContentsMargins(32, 44, 32, 44)
        zlay.setSpacing(18)
        zlay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel()
        badge.setFixedSize(80, 80)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background: rgba(0,120,212,0.12); border-radius: 16px;"
        )
        badge.setPixmap(svg_icon("box", 44, C_ACCENT_HI))
        zlay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Перетащите папку сюда")
        title.setStyleSheet(
            f"color: {C_TEXT}; font-size: 16px; font-weight: 600;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlay.addWidget(title)

        sub = QLabel(
            'или нажмите <span style="color:#3A9BE5;font-weight:600;">'
            "Добавить папку</span>, чтобы начать"
        )
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 13px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlay.addWidget(sub)

        hint = QLabel("Папки можно раскрывать и отмечать файлы галочками")
        hint.setStyleSheet(
            f"color: {C_TEXT_FAINT}; font-size: 11px; "
            f"border-top: 1px solid {C_PANEL_ALT}; padding-top: 10px;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlay.addWidget(hint)

        outer.addWidget(zone)


class BottomPanel(QWidget):
    pack_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("bottom")
        self.setStyleSheet(
            f"#bottom {{ background: {C_PANEL}; "
            f"border-top: 1px solid {C_BORDER}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)

        left = QVBoxLayout()
        left.setSpacing(2)
        self.summary = QLabel()
        self.summary.setStyleSheet(f"font-size: 13px; color: {C_TEXT};")
        self.estimate = QLabel()
        self.estimate.setStyleSheet(f"font-size: 11px; color: {C_TEXT_FAINT};")
        left.addWidget(self.summary)
        left.addWidget(self.estimate)
        lay.addLayout(left)
        lay.addStretch(1)

        self.pack_btn = QPushButton("Упаковать в ZIP")
        self.pack_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pack_btn.setIcon(QIcon(svg_icon("chevron", 14, "white")))
        self.pack_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.pack_btn.clicked.connect(self.pack_requested.emit)
        lay.addWidget(self.pack_btn)
        self.set_summary(0, 0)

    def set_summary(self, count: int, total_bytes: int):
        enabled = count > 0
        self.pack_btn.setEnabled(enabled)
        if enabled:
            self.summary.setText(
                f'<span style="color:{C_TEXT_DIM};">Выбрано: </span>'
                f"<b>{count}</b>"
                f'<span style="color:{C_TEXT_DIM};"> {plural_files(count)} '
                f"({human_size(total_bytes)})</span>"
            )
            approx = int(total_bytes * 0.78)
            secs = max(1, round(total_bytes / (35 * 1024 * 1024)))
            self.estimate.setText(
                f"≈ {human_size(approx)} после сжатия · ~{secs} сек"
            )
        else:
            self.summary.setText(
                f'<span style="color:{C_TEXT_DIM};">Выбрано: </span><b>0</b>'
                f'<span style="color:{C_TEXT_DIM};"> файлов</span>'
            )
            self.estimate.setText("Добавьте папку, чтобы начать")
        self._restyle(enabled)

    def _restyle(self, enabled: bool):
        if enabled:
            self.pack_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {C_ACCENT};
                    border: 1px solid {C_ACCENT_BR};
                    border-radius: 4px; padding: 11px 22px;
                    color: white; font-size: 14px; font-weight: 600;
                }}
                QPushButton:hover {{ background: #1A8AE0; }}
                QPushButton:pressed {{ background: #006ABE; }}
                """
            )
        else:
            self.pack_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {C_BORDER}; border: 1px solid #3a3a3a;
                    border-radius: 4px; padding: 11px 22px;
                    color: {C_TEXT_FAINT}; font-size: 14px; font-weight: 600;
                }}
                """
            )


class StatusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(24)
        self.setObjectName("status")
        self.setStyleSheet(
            f"#status {{ background: {C_BAR}; "
            f"border-top: 1px solid {C_BORDER}; }}"
            f"QLabel {{ color: {C_TEXT_DIM}; font-size: 11px; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {C_GREEN}; border-radius: 3px;")
        lay.addWidget(dot)
        self.left = QLabel("Готово")
        lay.addWidget(self.left)
        lay.addStretch(1)
        self.right = QLabel("0 элементов")
        lay.addWidget(self.right)

    def set_text(self, left: str, right: str):
        self.left.setText(left)
        self.right.setText(right)


class PackWorker(QThread):
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, zip_path: str, items: list[ArchiveItem]):
        super().__init__()
        self._zip_path = zip_path
        self._items = items
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            written = create_zip(
                self._zip_path,
                self._items,
                progress=lambda d, t, n: self.progress.emit(d, t, n),
                should_cancel=lambda: self._cancel,
            )
            self.done.emit(written)
        except InterruptedError:
            self.error.emit("Упаковка отменена")
        except Exception as exc:
            self.error.emit(str(exc))


ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_SIZE = Qt.ItemDataRole.UserRole + 1
ROLE_ARC = Qt.ItemDataRole.UserRole + 2
ROLE_ISFILE = Qt.ItemDataRole.UserRole + 3

RESIZE_MARGIN = 5


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick Zip")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(800, 600)
        self.resize(1040, 700)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setObjectName("root")
        self.setStyleSheet(f"#root {{ background: {C_WINDOW}; }}")

        self._file_items: list[QTreeWidgetItem] = []
        self._roots: set[str] = set()
        self._worker: PackWorker | None = None
        self._building = False
        self._summary_pending = False
        self._suggested_name = ""
        self._suggested_dir = ""
        self._last_target = "архив.zip"

        root = QVBoxLayout(self)
        root.setContentsMargins(
            RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN
        )
        root.setSpacing(0)

        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)
        root.addWidget(self._build_toolbar())

        self.stack = QStackedWidget()
        self.empty = EmptyState()
        self.tree = self._build_tree()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.tree)
        root.addWidget(self.stack, 1)

        self.bottom = BottomPanel()
        self.bottom.pack_requested.connect(self._pack)
        root.addWidget(self.bottom)

        self.status = StatusBar()
        root.addWidget(self.status)

        self._refresh_view()

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setStyleSheet(
            f"#toolbar {{ background: {C_PANEL}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        b_add = ToolbarButton("add_folder", "Добавить папку")
        b_add.clicked.connect(self._add_folder)
        sep = QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background: {C_BORDER};")
        b_clear = ToolbarButton("clear", "Очистить всё")
        b_clear.clicked.connect(self._clear_all)

        lay.addWidget(b_add)
        lay.addSpacing(4)
        lay.addWidget(sep)
        lay.addSpacing(4)
        lay.addWidget(b_clear)
        lay.addStretch(1)
        return bar

    def _build_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setColumnCount(3)
        tree.setHeaderHidden(False)
        tree.setHeaderLabels(["Имя", "Размер", "Путь"])
        tree.setUniformRowHeights(True)
        tree.setAlternatingRowColors(True)
        tree.setIndentation(16)
        tree.setIconSize(QSize(22, 22))
        tree.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        tree.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tree.headerItem().setTextAlignment(
            1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        hdr = tree.header()
        hdr.setFixedHeight(38)
        hdr.setStretchLastSection(False)
        hdr.setSortIndicatorShown(False)
        hdr.setSectionsClickable(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        tree.setColumnWidth(1, 110)
        tree.setColumnWidth(2, 300)

        tree.itemChanged.connect(self._on_item_changed)
        arrow_closed, arrow_open = branch_arrows()
        tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background: {C_PANEL};
                alternate-background-color: {C_PANEL_ALT};
                color: {C_TEXT}; font-size: 13px;
                border: none; outline: none;
            }}
            QHeaderView {{ background: {C_BAR}; }}
            QHeaderView::section {{
                background: {C_BAR}; color: {C_TEXT_DIM};
                font-size: 12px; font-weight: 600;
                border: 0px; border-bottom: 1px solid {C_BORDER};
                padding: 0 10px;
            }}
            QHeaderView::section:first {{ padding-left: 46px; }}
            QTreeView::item {{ height: 30px; border: none; }}
            QTreeView::item:hover {{ background: #2c2f33; }}
            QTreeView::item:selected {{
                background: transparent; color: {C_TEXT};
            }}
            QTreeView::branch {{ background: transparent; }}
            QTreeView::branch:selected, QTreeView::branch:hover {{
                background: transparent;
            }}
            QTreeView::branch:has-children:closed {{
                image: url("{arrow_closed}");
            }}
            QTreeView::branch:has-children:open {{
                image: url("{arrow_open}");
            }}
            QScrollBar:vertical {{
                background: {C_WINDOW}; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3a3a; border-radius: 5px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #4a4a4a; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QScrollBar:horizontal {{
                background: {C_WINDOW}; height: 10px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: #3a3a3a; border-radius: 5px; min-width: 30px;
            }}
            """
        )

        self._sel_all = TriCheckBox(hdr)
        self._sel_all.setGeometry(15, 9, 20, 20)
        self._sel_all.toggled.connect(self._on_select_all)
        self._sel_all.raise_()
        return tree

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку"
        )
        if folder:
            self.add_folder_path(folder)

    def add_folder_path(self, folder: str):
        folder = os.path.normpath(folder)
        if not os.path.isdir(folder):
            return
        if folder in self._roots:
            for i in range(self.tree.topLevelItemCount()):
                top = self.tree.topLevelItem(i)
                if top.data(0, ROLE_PATH) == folder:
                    self.tree.takeTopLevelItem(i)
                    break
            self._roots.discard(folder)
            self._file_items = [
                it for it in self._file_items if it.treeWidget() is not None
            ]

        base = os.path.dirname(folder)
        self._building = True
        top = QTreeWidgetItem(self.tree)
        top.setText(0, os.path.basename(folder) or folder)
        top.setIcon(0, folder_icon())
        top.setData(0, ROLE_PATH, folder)
        top.setData(0, ROLE_ISFILE, False)
        top.setData(0, ROLE_SIZE, 0)
        top.setText(2, folder)
        top.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsAutoTristate
        )
        total = self._build_dir(top, folder, base)
        top.setText(1, human_size(total))
        top.setData(0, ROLE_SIZE, total)
        top.setCheckState(0, Qt.CheckState.Checked)
        top.setExpanded(True)
        self._building = False

        self._roots.add(folder)
        self._suggested_name = os.path.basename(folder) or "архив"
        self._suggested_dir = base
        self._refresh_view()
        self.status.set_text(
            f"Добавлена папка «{os.path.basename(folder)}»",
            self._last_target,
        )

    def _build_dir(self, parent_item, dirpath: str, base: str) -> int:
        try:
            entries = list(os.scandir(dirpath))
        except OSError:
            return 0
        dirs, files = [], []
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    dirs.append(e.path)
                elif e.is_file(follow_symlinks=False):
                    files.append(e.path)
            except OSError:
                pass
        dirs.sort(key=lambda s: os.path.basename(s).lower())
        files.sort(key=lambda s: os.path.basename(s).lower())

        total = 0
        for d in dirs:
            di = QTreeWidgetItem(parent_item)
            di.setText(0, os.path.basename(d))
            di.setIcon(0, folder_icon())
            di.setData(0, ROLE_PATH, d)
            di.setData(0, ROLE_ISFILE, False)
            di.setText(2, d)
            di.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsAutoTristate
            )
            sub_total = self._build_dir(di, d, base)
            di.setText(1, human_size(sub_total))
            di.setData(0, ROLE_SIZE, sub_total)
            di.setCheckState(0, Qt.CheckState.Checked)
            total += sub_total

        for f in files:
            try:
                size = os.path.getsize(f)
            except OSError:
                size = 0
            arc = os.path.relpath(f, base).replace(os.sep, "/")
            fi = QTreeWidgetItem(parent_item)
            fi.setText(0, os.path.basename(f))
            fi.setIcon(0, tile_icon(f))
            fi.setText(1, human_size(size))
            fi.setText(2, os.path.dirname(f))
            fi.setData(0, ROLE_PATH, f)
            fi.setData(0, ROLE_SIZE, size)
            fi.setData(0, ROLE_ARC, arc)
            fi.setData(0, ROLE_ISFILE, True)
            fi.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            fi.setCheckState(0, Qt.CheckState.Checked)
            fi.setTextAlignment(
                1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._file_items.append(fi)
            total += size

        return total

    def add_single_file(self, path: str):
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            return
        if any(it.data(0, ROLE_PATH) == path for it in self._file_items):
            return
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        self._building = True
        fi = QTreeWidgetItem(self.tree)
        fi.setText(0, os.path.basename(path))
        fi.setIcon(0, tile_icon(path))
        fi.setText(1, human_size(size))
        fi.setText(2, os.path.dirname(path))
        fi.setData(0, ROLE_PATH, path)
        fi.setData(0, ROLE_SIZE, size)
        fi.setData(0, ROLE_ARC, os.path.basename(path))
        fi.setData(0, ROLE_ISFILE, True)
        fi.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        fi.setCheckState(0, Qt.CheckState.Checked)
        fi.setTextAlignment(
            1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._file_items.append(fi)
        self._building = False
        if not self._suggested_dir:
            self._suggested_dir = os.path.dirname(path)
        self._refresh_view()

    def _clear_all(self):
        if self.tree.topLevelItemCount() == 0:
            return
        self.tree.clear()
        self._file_items.clear()
        self._roots.clear()
        self._suggested_name = ""
        self._suggested_dir = ""
        self._refresh_view()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            if os.path.isdir(local):
                self.add_folder_path(local)
            elif os.path.isfile(local):
                self.add_single_file(local)

    def _on_select_all(self, value: bool):
        state = (
            Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
        )
        self.tree.blockSignals(True)
        for it in self._file_items:
            it.setCheckState(0, state)
        self.tree.blockSignals(False)
        self._recompute_summary()

    def _on_item_changed(self, _item, _column):
        if self._building or self._summary_pending:
            return
        self._summary_pending = True
        QTimer.singleShot(0, self._recompute_summary)

    def _refresh_view(self):
        has = self.tree.topLevelItemCount() > 0
        self.stack.setCurrentIndex(1 if has else 0)
        self._recompute_summary()

    def _recompute_summary(self):
        self._summary_pending = False
        total = len(self._file_items)
        sel = 0
        size = 0
        for it in self._file_items:
            if it.checkState(0) == Qt.CheckState.Checked:
                sel += 1
                size += int(it.data(0, ROLE_SIZE) or 0)
        self.bottom.set_summary(sel, size)

        if total == 0 or sel == 0:
            self._sel_all.set_state(False)
        elif sel == total:
            self._sel_all.set_state(True)
        else:
            self._sel_all.set_state("mixed")

        if total == 0:
            self.status.set_text("Готово", "0 элементов")
        else:
            self.status.set_text(
                f"Загружено {total} {plural_files(total)} · "
                f"{sel} выбрано для архива",
                self._last_target,
            )

    def _checked_items(self) -> list[ArchiveItem]:
        out = []
        for it in self._file_items:
            if it.checkState(0) != Qt.CheckState.Checked:
                continue
            path = it.data(0, ROLE_PATH)
            arc = it.data(0, ROLE_ARC) or os.path.basename(path)
            size = int(it.data(0, ROLE_SIZE) or 0)
            out.append(ArchiveItem(src=path, arcname=arc, size=size))
        return out

    def _pack(self):
        items = self._checked_items()
        if not items:
            return
        base_name = self._suggested_name or "архив"
        init_dir = self._suggested_dir or os.path.expanduser("~")
        init_path = os.path.join(init_dir, base_name + ".zip")
        target, _ = QFileDialog.getSaveFileName(
            self, "Сохранить архив", init_path, "ZIP-архив (*.zip)"
        )
        if not target:
            return
        if not target.lower().endswith(".zip"):
            target += ".zip"
        self._last_target = os.path.basename(target)

        self.bottom.pack_btn.setEnabled(False)
        self._worker = PackWorker(target, items)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(lambda n: self._on_done(n, target))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, done: int, total: int, name: str):
        pct = int(done * 100 / total) if total else 0
        self.status.set_text(
            f"Упаковка… {pct}% · {name}", self._last_target
        )

    def _on_done(self, written: int, target: str):
        self.bottom.pack_btn.setEnabled(True)
        self.status.set_text(
            f"Готово · записано {written} {plural_files(written)}",
            os.path.basename(target),
        )
        QMessageBox.information(
            self,
            "Quick Zip",
            f"Архив создан:\n{target}\n\n"
            f"Записано файлов: {written}\n"
            f"Размер архива: {human_size(os.path.getsize(target))}",
        )

    def _on_error(self, message: str):
        self.bottom.pack_btn.setEnabled(True)
        self._recompute_summary()
        if message == "Упаковка отменена":
            self.status.set_text("Упаковка отменена", self._last_target)
            return
        QMessageBox.critical(
            self, "Quick Zip", f"Не удалось создать архив:\n{message}"
        )

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _edges_at(self, pos):
        if self.isMaximized():
            return Qt.Edge(0)
        r = self.rect()
        m = RESIZE_MARGIN + 2
        edges = Qt.Edge(0)
        if pos.x() <= m:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= r.width() - m:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= m:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= r.height() - m:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _cursor_for(self, edges):
        le = bool(edges & Qt.Edge.LeftEdge)
        re = bool(edges & Qt.Edge.RightEdge)
        te = bool(edges & Qt.Edge.TopEdge)
        be = bool(edges & Qt.Edge.BottomEdge)
        if (le and te) or (re and be):
            return Qt.CursorShape.SizeFDiagCursor
        if (re and te) or (le and be):
            return Qt.CursorShape.SizeBDiagCursor
        if le or re:
            return Qt.CursorShape.SizeHorCursor
        if te or be:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mouseMoveEvent(self, event):
        edges = self._edges_at(event.position().toPoint())
        self.setCursor(self._cursor_for(edges))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self._edges_at(event.position().toPoint())
            if edges != Qt.Edge(0):
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
        super().mousePressEvent(event)


def _dark_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C_WINDOW))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(C_PANEL))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C_PANEL_ALT))
    pal.setColor(QPalette.ColorRole.Text, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(C_PANEL_ALT))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(C_BAR))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C_TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C_ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(C_TEXT_DIM))
    return pal


def run() -> int:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "QuickZip.Desktop.App"
            )
        except Exception:
            pass

    QApplication.setApplicationName("Quick Zip")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    icon = app_icon()
    app.setWindowIcon(icon)
    win = MainWindow()
    win.setWindowIcon(icon)
    win.show()
    return app.exec()
