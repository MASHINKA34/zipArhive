from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QProxyStyle, QStyle

from ui.theme import C_ACCENT, C_WINDOW

_ARROW_COLOR = QColor("#c8c8c8")
_BOX_BORDER = QColor("#555555")
_CHECK_COLOR = QColor("#ffffff")

_CLOSED = ((-1.8, -3.6), (1.8, 0.0), (-1.8, 3.6))
_OPEN = ((-3.6, -1.8), (0.0, 1.8), (3.6, -1.8))


class TreeStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PrimitiveElement.PE_IndicatorBranch:
            self._draw_branch(option, painter)
            return
        if element == (
            QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck
        ):
            self._draw_check(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    @staticmethod
    def _draw_branch(option, painter: QPainter) -> None:
        state = option.state
        if not (state & QStyle.StateFlag.State_Children):
            return
        points = _OPEN if state & QStyle.StateFlag.State_Open else _CLOSED
        center = QPointF(option.rect.center()) + QPointF(0.5, 0.5)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(_ARROW_COLOR, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(
            QPolygonF([center + QPointF(x, y) for x, y in points])
        )
        painter.restore()

    @staticmethod
    def _draw_check(option, painter: QPainter) -> None:
        rect = option.rect
        side = min(rect.width(), rect.height(), 18)
        box = QRectF(0, 0, side, side)
        box.moveCenter(QPointF(rect.center()) + QPointF(0.5, 0.5))
        state = option.state
        checked = bool(state & QStyle.StateFlag.State_On)
        partial = bool(state & QStyle.StateFlag.State_NoChange)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(box, 3, 3)
        if checked or partial:
            painter.fillPath(path, QColor(C_ACCENT))
            painter.setPen(QPen(QColor(C_ACCENT), 1))
        else:
            painter.fillPath(path, QColor(C_WINDOW))
            painter.setPen(QPen(_BOX_BORDER, 1.4))
        painter.drawPath(path)

        if checked:
            pen = QPen(_CHECK_COLOR, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            unit = box.width() / 20.0
            origin = box.topLeft()
            painter.drawPolyline(QPolygonF([
                origin + QPointF(5 * unit, 10 * unit),
                origin + QPointF(8.5 * unit, 14 * unit),
                origin + QPointF(15 * unit, 6.5 * unit),
            ]))
        elif partial:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_CHECK_COLOR)
            inset = box.width() * 0.26
            painter.drawRoundedRect(
                QRectF(
                    box.left() + inset,
                    box.center().y() - box.height() * 0.06,
                    box.width() - inset * 2,
                    box.height() * 0.12,
                ),
                1, 1,
            )
        painter.restore()
