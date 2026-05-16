from __future__ import annotations

import os
import sys

from PyQt6.QtCore import (
    QByteArray,
    QPointF,
    QRectF,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.archiver import (
    ArchiveItem,
    create_zip,
    expand_folder,
    human_size,
    make_item,
    make_items,
    plural_files,
)

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
    "zip": ("#C9952B", "ZIP"), "rar": ("#C9952B", "RAR"),
    "7z": ("#C9952B", "7Z"), "gz": ("#C9952B", "GZ"),
    "tar": ("#C9952B", "TAR"),
    "exe": ("#6B7280", "EXE"), "msi": ("#6B7280", "MSI"),
    "dll": ("#6B7280", "DLL"), "iso": ("#7A6CA8", "ISO"),
}

_SVG = {
    "add_file": (
        '<svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M9 1.5H4.5A1.5 1.5 0 0 0 3 3v10a1.5 1.5 0 0 0 1.5 1.5h7A1.5 1.5 0 0 0 13 13V5.5L9 1.5Z" stroke="{c}" stroke-width="1.1" stroke-linejoin="round"/>'
        '<path d="M9 1.5V5.5H13" stroke="{c}" stroke-width="1.1" stroke-linejoin="round"/>'
        '<path d="M8 8V12M6 10H10" stroke="{c}" stroke-width="1.1" stroke-linecap="round"/></svg>'
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
    "folder": (
        '<svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M1.5 4.2C1.5 3.5 2 3 2.7 3h3.1c.3 0 .6.13.83.35l.9.9c.22.22.52.35.83.35H13.3c.66 0 1.2.54 1.2 1.2v6.6c0 .66-.54 1.2-1.2 1.2H2.7c-.66 0-1.2-.54-1.2-1.2V4.2Z" fill="{c}"/></svg>'
    ),
}


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


def file_tile(path: str, size: int = 28) -> QPixmap:
    ext = kind_of(path)
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
    body.addRoundedRect(rect, 6, 6)
    p.fillPath(body, base)

    fold = 9
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
        f.setPixelSize(9 if len(label) <= 3 else 7)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(0, 2, size, size - 2),
                   Qt.AlignmentFlag.AlignCenter, label)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 215))
        line_w = 14.0
        x = (size - line_w) / 2
        for i, y in enumerate((10.0, 14.0, 18.0)):
            w = line_w if i < 2 else line_w * 0.6
            p.drawRoundedRect(QRectF(x, y, w, 2.2), 1, 1)

    p.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def folder_pixmap(size: int = 28) -> QPixmap:
    return svg_icon("folder", size, "#D8A23A")


def app_icon() -> QIcon:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico = os.path.join(here, "assets", "icons", "app.ico")
    if os.path.exists(ico):
        return QIcon(ico)
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(C_ACCENT))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    f = QFont("Segoe UI", 34)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "Z")
    p.end()
    return QIcon(pm)


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

        glyph = QLabel("Z")
        glyph.setFixedSize(16, 16)
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setStyleSheet(
            f"background: {C_ACCENT}; border-radius: 3px; color: white; "
            f"font-size: 9px; font-weight: 700;"
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


class FileRow(QWidget):
    def __init__(self, record: dict, index: int, on_toggle):
        super().__init__()
        self.record = record
        self._on_toggle = on_toggle
        self.setFixedHeight(44)
        bg = C_PANEL if index % 2 == 0 else C_PANEL_ALT
        self.setStyleSheet(
            f"FileRow {{ background: {bg}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        cb_wrap = QWidget()
        cb_wrap.setFixedWidth(44)
        cb_lay = QHBoxLayout(cb_wrap)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.checkbox = TriCheckBox()
        self.checkbox.set_state(record["checked"])
        self.checkbox.toggled.connect(self._toggled)
        cb_lay.addWidget(self.checkbox)
        lay.addWidget(cb_wrap)

        icon_wrap = QWidget()
        icon_wrap.setFixedWidth(40)
        icon_lay = QHBoxLayout(icon_wrap)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel()
        icon.setPixmap(file_tile(record["path"]))
        icon_lay.addWidget(icon)
        lay.addWidget(icon_wrap)

        name = QLabel(record["name"])
        name.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13px; padding-right: 12px;"
        )
        name.setToolTip(record["name"])
        lay.addWidget(name, 1)

        size = QLabel(human_size(record["size"]))
        size.setFixedWidth(90)
        size.setStyleSheet(f"color: {C_TEXT_SOFT}; font-size: 13px;")
        lay.addWidget(size)

        path = QLabel()
        path.setFixedWidth(220)
        path.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 12px; "
            f"font-family: 'Consolas','Courier New'; padding-right: 16px;"
        )
        path.setToolTip(record["path"])
        metrics = path.fontMetrics()
        path.setText(
            metrics.elidedText(record["dir"], Qt.TextElideMode.ElideMiddle, 196)
        )
        lay.addWidget(path)

    def _toggled(self, value: bool):
        self.record["checked"] = value
        self._on_toggle()


class ListHeader(QWidget):
    def __init__(self, on_select_all):
        super().__init__()
        self.setFixedHeight(37)
        self.setStyleSheet(
            f"ListHeader {{ background: {C_BAR}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        cb_wrap = QWidget()
        cb_wrap.setFixedWidth(44)
        cb_lay = QHBoxLayout(cb_wrap)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.checkbox = TriCheckBox()
        self.checkbox.toggled.connect(on_select_all)
        cb_lay.addWidget(self.checkbox)
        lay.addWidget(cb_wrap)

        lay.addSpacing(40)

        style = f"color: {C_TEXT_DIM}; font-size: 12px; font-weight: 600;"
        name = QLabel("Имя")
        name.setStyleSheet(style)
        lay.addWidget(name, 1)
        size = QLabel("Размер")
        size.setFixedWidth(90)
        size.setStyleSheet(style)
        lay.addWidget(size)
        path = QLabel("Путь")
        path.setFixedWidth(220)
        path.setStyleSheet(style + " padding-right: 16px;")
        lay.addWidget(path)


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

        title = QLabel("Перетащите файлы сюда")
        title.setStyleSheet(
            f"color: {C_TEXT}; font-size: 16px; font-weight: 600;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlay.addWidget(title)

        sub = QLabel(
            'или нажмите <span style="color:#3A9BE5;font-weight:600;">'
            "Добавить файлы</span>, чтобы начать"
        )
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 13px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zlay.addWidget(sub)

        hint = QLabel("Поддерживаются  любые типы файлов  ·  до 4 ГБ")
        hint.setStyleSheet(
            f"color: {C_TEXT_FAINT}; font-size: 11px; "
            f"font-family: 'Consolas','Courier New'; "
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
            self.estimate.setText("Добавьте файлы, чтобы начать")
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
ROLE_ISDIR = Qt.ItemDataRole.UserRole + 1
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2


class FolderSelectDialog(QDialog):
    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        self._root = os.path.normpath(root)
        self._mute = False
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.resize(760, 580)
        self.setMinimumSize(560, 440)
        self.setObjectName("dlg")
        self.setStyleSheet(
            f"""
            #dlg {{ background: {C_WINDOW}; border: 1px solid {C_BORDER}; }}
            QLabel {{ color: {C_TEXT}; }}
            QTreeWidget {{
                background: {C_WINDOW}; border: 1px solid {C_BORDER};
                color: {C_TEXT}; font-size: 13px; outline: none;
            }}
            QTreeWidget::item {{ height: 26px; }}
            QTreeWidget::item:selected {{ background: #2d3a47; }}
            QHeaderView::section {{
                background: {C_BAR}; color: {C_TEXT_DIM};
                border: none; border-bottom: 1px solid {C_BORDER};
                padding: 6px 8px; font-size: 12px; font-weight: 600;
            }}
            QScrollBar:vertical {{
                background: {C_WINDOW}; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3a3a; border-radius: 5px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #4a4a4a; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QCheckBox {{ color: {C_TEXT_SOFT}; font-size: 12px; }}
            """
        )

        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setObjectName("dbar")
        bar.setStyleSheet(
            f"#dbar {{ background: {C_BAR}; "
            f"border-bottom: 1px solid {C_BORDER}; }}"
        )
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 0, 6, 0)
        cap = QLabel("Выбор файлов и папок")
        cap.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        bl.addWidget(cap)
        bl.addStretch(1)
        close = CaptionButton("✕", close=True)
        close.clicked.connect(self.reject)
        bl.addWidget(close)
        self._bar = bar
        bar.mousePressEvent = self._bar_press
        root_lay.addWidget(bar)

        path_lbl = QLabel(self._root)
        path_lbl.setStyleSheet(
            f"color: {C_TEXT_DIM}; font-size: 12px; "
            f"font-family: 'Consolas','Courier New'; "
            f"background: {C_PANEL}; padding: 8px 14px; "
            f"border-bottom: 1px solid {C_BORDER};"
        )
        root_lay.addWidget(path_lbl)

        body = QWidget()
        body.setStyleSheet(f"background: {C_WINDOW};")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(14, 12, 14, 12)
        body_lay.setSpacing(10)

        self._all_cb = QCheckBox("Выбрать всё")
        self._all_cb.setChecked(True)
        self._all_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._all_cb.toggled.connect(self._toggle_all)
        body_lay.addWidget(self._all_cb)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Имя", "Размер"])
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 110)
        self.tree.itemExpanded.connect(self._on_expand)
        self.tree.itemChanged.connect(self._on_item_changed)
        body_lay.addWidget(self.tree, 1)

        root_lay.addWidget(body, 1)

        foot = QWidget()
        foot.setStyleSheet(
            f"background: {C_PANEL}; border-top: 1px solid {C_BORDER};"
        )
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(14, 12, 14, 12)
        self._hint = QLabel("")
        self._hint.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px;")
        fl.addWidget(self._hint)
        fl.addStretch(1)

        cancel = QPushButton("Отмена")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(
            f"""
            QPushButton {{
                background: {C_PANEL_ALT}; border: 1px solid {C_BORDER};
                border-radius: 4px; padding: 9px 18px; color: {C_TEXT};
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #323232; }}
            """
        )
        cancel.clicked.connect(self.reject)
        fl.addWidget(cancel)

        add = QPushButton("Добавить в список")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.setStyleSheet(
            f"""
            QPushButton {{
                background: {C_ACCENT}; border: 1px solid {C_ACCENT_BR};
                border-radius: 4px; padding: 9px 18px; color: white;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #1A8AE0; }}
            """
        )
        add.clicked.connect(self.accept)
        fl.addWidget(add)
        root_lay.addWidget(foot)

        self._folder_icon = QIcon(folder_pixmap(22))
        self._populate(self.tree.invisibleRootItem(), self._root, True)

    def _bar_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()

    def _make_item(self, parent, path: str, is_dir: bool, checked: bool):
        it = QTreeWidgetItem(parent)
        it.setText(0, os.path.basename(path) or path)
        it.setData(0, ROLE_PATH, path)
        it.setData(0, ROLE_ISDIR, is_dir)
        it.setData(0, ROLE_LOADED, False)
        it.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        it.setCheckState(
            0,
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
        )
        if is_dir:
            it.setIcon(0, self._folder_icon)
            placeholder = QTreeWidgetItem(it)
            placeholder.setData(0, ROLE_PATH, "")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            it.setIcon(0, QIcon(file_tile(path, 22)))
            try:
                it.setText(1, human_size(os.path.getsize(path)))
            except OSError:
                it.setText(1, "")
            it.setTextAlignment(
                1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        return it

    def _populate(self, parent_item, folder: str, checked: bool):
        try:
            entries = list(os.scandir(folder))
        except OSError:
            return
        dirs, files = [], []
        for e in entries:
            try:
                if e.is_dir():
                    dirs.append(e.path)
                else:
                    files.append(e.path)
            except OSError:
                pass
        dirs.sort(key=lambda s: os.path.basename(s).lower())
        files.sort(key=lambda s: os.path.basename(s).lower())
        self._mute = True
        for d in dirs:
            self._make_item(parent_item, d, True, checked)
        for f in files:
            self._make_item(parent_item, f, False, checked)
        self._mute = False

    def _on_expand(self, item: QTreeWidgetItem):
        if item.data(0, ROLE_LOADED):
            return
        item.setData(0, ROLE_LOADED, True)
        self._mute = True
        for i in reversed(range(item.childCount())):
            item.removeChild(item.child(i))
        self._mute = False
        checked = item.checkState(0) == Qt.CheckState.Checked
        self._populate(item, item.data(0, ROLE_PATH), checked)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != 0 or self._mute:
            return
        state = item.checkState(0)
        self._mute = True
        if state in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
            self._apply_down(item, state)
        self._update_ancestors(item.parent())
        self._mute = False

    def _apply_down(self, item: QTreeWidgetItem, state):
        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() == Qt.ItemFlag.NoItemFlags:
                continue
            child.setCheckState(0, state)
            self._apply_down(child, state)

    def _update_ancestors(self, item):
        while item is not None:
            states = []
            for i in range(item.childCount()):
                child = item.child(i)
                if child.flags() == Qt.ItemFlag.NoItemFlags:
                    continue
                states.append(child.checkState(0))
            if states and all(s == Qt.CheckState.Checked for s in states):
                item.setCheckState(0, Qt.CheckState.Checked)
            elif states and all(
                s == Qt.CheckState.Unchecked for s in states
            ):
                item.setCheckState(0, Qt.CheckState.Unchecked)
            else:
                item.setCheckState(0, Qt.CheckState.PartiallyChecked)
            item = item.parent()

    def _toggle_all(self, checked: bool):
        state = (
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        root = self.tree.invisibleRootItem()
        self._mute = True
        for i in range(root.childCount()):
            top = root.child(i)
            top.setCheckState(0, state)
            self._apply_down(top, state)
        self._mute = False

    def _collect(self, item, out: list[str]):
        is_dir = item.data(0, ROLE_ISDIR)
        path = item.data(0, ROLE_PATH)
        state = item.checkState(0)
        if not is_dir:
            if state == Qt.CheckState.Checked and path:
                out.append(path)
            return
        if state == Qt.CheckState.Unchecked:
            return
        loaded = item.data(0, ROLE_LOADED)
        if state == Qt.CheckState.Checked and not loaded:
            for r, _d, fs in os.walk(path):
                for f in fs:
                    out.append(os.path.join(r, f))
            return
        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() == Qt.ItemFlag.NoItemFlags:
                continue
            self._collect(child, out)

    def selected_files(self) -> list[str]:
        out: list[str] = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect(root.child(i), out)
        seen = set()
        unique = []
        for p in out:
            np = os.path.normpath(p)
            if np not in seen and os.path.isfile(np):
                seen.add(np)
                unique.append(np)
        return unique


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

        self._records: list[dict] = []
        self._rows: list[FileRow] = []
        self._worker: PackWorker | None = None
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

        self.header = ListHeader(self._on_select_all)
        root.addWidget(self.header)

        self.stack = QStackedWidget()
        self.empty = EmptyState()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(
            f"""
            QScrollArea {{ background: {C_WINDOW}; border: none; }}
            QScrollBar:vertical {{
                background: {C_WINDOW}; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3a3a; border-radius: 5px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #4a4a4a; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            """
        )
        self.list_host = QWidget()
        self.list_host.setStyleSheet(f"background: {C_WINDOW};")
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(0)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.list_host)

        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.scroll)
        root.addWidget(self.stack, 1)

        self.bottom = BottomPanel()
        self.bottom.pack_requested.connect(self._pack)
        root.addWidget(self.bottom)

        self.status = StatusBar()
        root.addWidget(self.status)

        self._refresh()

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

        b_add = ToolbarButton("add_file", "Добавить файлы")
        b_add.clicked.connect(self._add_via_dialog)
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

    def _add_records(self, items: list[ArchiveItem]):
        existing = {r["path"] for r in self._records}
        added = 0
        for it in items:
            if it.src in existing:
                continue
            existing.add(it.src)
            self._records.append({
                "path": it.src,
                "arcname": it.arcname,
                "name": os.path.basename(it.src),
                "dir": os.path.dirname(it.src),
                "size": it.size,
                "checked": True,
            })
            added += 1
        self._refresh()
        return added

    def _add_via_dialog(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с файлами"
        )
        if not folder:
            return
        folder = os.path.normpath(folder)
        dlg = FolderSelectDialog(folder, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        files = dlg.selected_files()
        if not files:
            self.status.set_text("Ничего не выбрано", self._last_target)
            return
        base = os.path.dirname(folder)
        self._suggested_name = os.path.basename(folder)
        self._suggested_dir = base
        added = self._add_records(make_items(files, base))
        self.status.set_text(
            f"Добавлено {added} {plural_files(added)} из «"
            f"{os.path.basename(folder)}»",
            self._last_target,
        )

    def _clear_all(self):
        if not self._records:
            return
        self._records.clear()
        self._suggested_name = ""
        self._suggested_dir = ""
        self._refresh()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        items: list[ArchiveItem] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            if os.path.isdir(local):
                items.extend(expand_folder(local))
                self._suggested_name = os.path.basename(
                    os.path.normpath(local)
                )
                self._suggested_dir = os.path.dirname(
                    os.path.normpath(local)
                )
            elif os.path.isfile(local):
                items.append(make_item(local))
        if items:
            self._add_records(items)

    def _on_select_all(self, value: bool):
        for rec in self._records:
            rec["checked"] = value
        for row in self._rows:
            row.checkbox.set_state(value)
        self._update_summary()

    def _refresh(self):
        while self.list_lay.count() > 1:
            taken = self.list_lay.takeAt(0)
            w = taken.widget()
            if w is not None:
                w.deleteLater()
        self._rows.clear()

        for idx, rec in enumerate(self._records):
            row = FileRow(rec, idx, self._update_summary)
            self._rows.append(row)
            self.list_lay.insertWidget(idx, row)

        has = bool(self._records)
        self.stack.setCurrentIndex(1 if has else 0)
        self.header.setVisible(has)
        self._update_summary()

    def _update_summary(self):
        total = len(self._records)
        checked = [r for r in self._records if r["checked"]]
        sel = len(checked)
        size = sum(r["size"] for r in checked)
        self.bottom.set_summary(sel, size)

        if total == 0 or sel == 0:
            self.header.checkbox.set_state(False)
        elif sel == total:
            self.header.checkbox.set_state(True)
        else:
            self.header.checkbox.set_state("mixed")

        if total == 0:
            self.status.set_text("Готово", "0 элементов")
        else:
            self.status.set_text(
                f"Загружено {total} {plural_files(total)} · "
                f"{sel} выбрано для архива",
                self._last_target,
            )

    def _pack(self):
        checked = [r for r in self._records if r["checked"]]
        if not checked:
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

        items = [
            ArchiveItem(src=r["path"], arcname=r["arcname"], size=r["size"])
            for r in checked
        ]
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
        self._update_summary()
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


def run() -> int:
    QApplication.setApplicationName("Quick Zip")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.setWindowIcon(app_icon())
    win.show()
    return app.exec()
