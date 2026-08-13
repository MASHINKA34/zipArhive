from __future__ import annotations

import os
import sys
from functools import lru_cache

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QFileIconProvider

from core.formatting import extension_of

TYPE_MAP: dict[str, tuple[str, str]] = {
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

DEFAULT_TILE = ("#5A6470", "")

SVG_SOURCES = {
    "add_folder": (
        '<svg viewBox="0 0 16 16" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M1.75 4.25C1.75 3.56 2.31 3 3 3h3.17c.33 0 .64.13.87.36l.85'
        '.85c.23.23.55.36.88.36H13c.69 0 1.25.56 1.25 1.25v6.43c0 .69-.56 1.25'
        '-1.25 1.25H3c-.69 0-1.25-.56-1.25-1.25V4.25Z" stroke="{c}" '
        'stroke-width="1.1" stroke-linejoin="round"/>'
        '<path d="M8 8V11.5M6.25 9.75H9.75" stroke="{c}" stroke-width="1.1" '
        'stroke-linecap="round"/></svg>'
    ),
    "add_file": (
        '<svg viewBox="0 0 16 16" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M9 1.75H4.5c-.69 0-1.25.56-1.25 1.25v10c0 .69.56 1.25 1.25 '
        '1.25h7c.69 0 1.25-.56 1.25-1.25V5.5L9 1.75Z" stroke="{c}" '
        'stroke-width="1.1" stroke-linejoin="round"/>'
        '<path d="M8.9 2v3.4h3.6" stroke="{c}" stroke-width="1.1" '
        'stroke-linejoin="round"/></svg>'
    ),
    "clear": (
        '<svg viewBox="0 0 16 16" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M3 4.5h10M6.5 4.5V3a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.5M4.5 '
        '4.5l.6 8.1A1 1 0 0 0 6.1 13.5h3.8a1 1 0 0 0 1-.9l.6-8.1" '
        'stroke="{c}" stroke-width="1.1" stroke-linecap="round" '
        'stroke-linejoin="round"/></svg>'
    ),
    "box": (
        '<svg viewBox="0 0 64 64" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M32 8L54 18V44L32 56L10 44V18L32 8Z" stroke="{c}" '
        'stroke-width="1.5" stroke-linejoin="round"/>'
        '<path d="M10 18L32 28L54 18M32 28V56" stroke="{c}" '
        'stroke-width="1.5" stroke-linejoin="round"/>'
        '<path d="M21 13L43 23" stroke="{c}" stroke-width="1.5" '
        'stroke-linejoin="round" stroke-dasharray="2 2"/></svg>'
    ),
    "chevron": (
        '<svg viewBox="0 0 16 16" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M6 4L10 8L6 12" stroke="{c}" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
}


def asset_path(*parts: str) -> str:
    root = getattr(sys, "_MEIPASS", None)
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, *parts)


def device_ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


@lru_cache(maxsize=128)
def _svg_pixmap(name: str, size: int, color: str, ratio: float) -> QPixmap:
    pixels = max(1, round(size * ratio))
    data = QByteArray(SVG_SOURCES[name].format(c=color).encode("utf-8"))
    renderer = QSvgRenderer(data)
    pixmap = QPixmap(pixels, pixels)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def svg_pixmap(name: str, size: int, color: str) -> QPixmap:
    return _svg_pixmap(name, size, color, device_ratio())


def svg_icon(name: str, size: int, color: str) -> QIcon:
    return QIcon(svg_pixmap(name, size, color))


@lru_cache(maxsize=512)
def _tile_pixmap(ext: str, size: int, ratio: float) -> QPixmap:
    color, label = TYPE_MAP.get(ext, DEFAULT_TILE)
    if ext and ext not in TYPE_MAP:
        label = ext.upper()[:4]
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(ratio, ratio)

    base = QColor(color)
    body = QPainterPath()
    body.addRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 5, 5)
    painter.fillPath(body, base)

    fold = 7
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(base.darker(140))
    painter.drawPolygon(QPolygonF([
        QPointF(size - fold, 0.5),
        QPointF(size - 0.5, 0.5),
        QPointF(size - 0.5, fold),
    ]))
    painter.setPen(base.lighter(118))
    painter.drawLine(QPointF(size - fold, 0.5), QPointF(size - fold, fold))
    painter.drawLine(QPointF(size - fold, fold), QPointF(size - 0.5, fold))

    if label:
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(8 if len(label) <= 3 else 6)
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(
            QRectF(0, 1, size, size - 1),
            Qt.AlignmentFlag.AlignCenter, label,
        )
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 215))
        width = size * 0.5
        left = (size - width) / 2
        for index, top in enumerate((size * 0.34, size * 0.5, size * 0.66)):
            line = width if index < 2 else width * 0.6
            painter.drawRoundedRect(QRectF(left, top, line, 1.8), 1, 1)

    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


@lru_cache(maxsize=512)
def _tile_icon(ext: str, size: int, ratio: float) -> QIcon:
    return QIcon(_tile_pixmap(ext, size, ratio))


def file_icon(name: str, size: int = 22) -> QIcon:
    return _tile_icon(extension_of(name), size, device_ratio())


@lru_cache(maxsize=1)
def folder_icon() -> QIcon:
    return QFileIconProvider().icon(QFileIconProvider.IconType.Folder)


def _fallback_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    body = QPainterPath()
    radius = size * 0.22
    body.addRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), radius, radius)
    painter.fillPath(body, QColor("#0078D4"))
    renderer = QSvgRenderer(
        QByteArray(SVG_SOURCES["box"].format(c="#ffffff").encode("utf-8"))
    )
    inset = size * 0.17
    renderer.render(painter, QRectF(inset, inset, size - inset * 2,
                                    size - inset * 2))
    painter.end()
    return pixmap


@lru_cache(maxsize=1)
def app_icon() -> QIcon:
    path = asset_path("assets", "icons", "app.ico")
    if os.path.exists(path):
        icon = QIcon(path)
        if not icon.isNull() and icon.availableSizes():
            return icon
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_fallback_pixmap(size))
    return icon
