from __future__ import annotations

import logging
import os
import time

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal

from core.formatting import human_size
from core.scanner import Node, set_checked
from ui.icons import file_icon, folder_icon

log = logging.getLogger("quickzip.model")

_DISPLAY_ROLE = Qt.ItemDataRole.DisplayRole.value
_DECORATION_ROLE = Qt.ItemDataRole.DecorationRole.value
_CHECK_ROLE = Qt.ItemDataRole.CheckStateRole.value
_ALIGN_ROLE = Qt.ItemDataRole.TextAlignmentRole.value
_TOOLTIP_ROLE = Qt.ItemDataRole.ToolTipRole.value
_CHECK_ROLES = [_CHECK_ROLE]
_RIGHT_ALIGN = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
_CHECKED = Qt.CheckState.Checked
_PARTIAL = Qt.CheckState.PartiallyChecked
_UNCHECKED = Qt.CheckState.Unchecked
_CELL_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
_NAME_FLAGS = _CELL_FLAGS | Qt.ItemFlag.ItemIsUserCheckable
_NO_FLAGS = Qt.ItemFlag.NoItemFlags
_HEADERS = ("Имя", "Размер", "Путь")
_COLUMNS = len(_HEADERS)


class FileTreeModel(QAbstractItemModel):
    selection_changed = pyqtSignal()
    subtree_checked = pyqtSignal(QModelIndex)

    HEADERS = _HEADERS

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._roots: list[Node] = []

    @property
    def roots(self) -> list[Node]:
        return self._roots

    def is_empty(self) -> bool:
        return not self._roots

    def node_at(self, index: QModelIndex) -> Node | None:
        if not index.isValid():
            return None
        return index.internalPointer()

    # The methods below are called by Qt for every visible cell (and for
    # every expanded row when UI Automation clients walk the window), so
    # they avoid helpers such as hasIndex() that call back into Python.
    def index(self, row, column, parent=QModelIndex()) -> QModelIndex:
        if parent.isValid():
            if parent.column() != 0:
                return QModelIndex()
            children = parent.internalPointer().children
            if not children:
                return QModelIndex()
        else:
            children = self._roots
        if 0 <= row < len(children) and 0 <= column < _COLUMNS:
            return self.createIndex(row, column, children[row])
        return QModelIndex()

    def parent(self, index=QModelIndex()) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        parent = index.internalPointer().parent
        if parent is None:
            return QModelIndex()
        return self.createIndex(parent.row, 0, parent)

    def rowCount(self, parent=QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._roots)
        if parent.column() != 0:
            return 0
        children = parent.internalPointer().children
        return len(children) if children else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return _COLUMNS

    def hasChildren(self, parent=QModelIndex()) -> bool:
        if not parent.isValid():
            return bool(self._roots)
        return bool(parent.internalPointer().children)

    def headerData(self, section, orientation, role=_DISPLAY_ROLE):
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == _DISPLAY_ROLE and 0 <= section < _COLUMNS:
            return _HEADERS[section]
        if role == _ALIGN_ROLE and section == 1:
            return _RIGHT_ALIGN
        return None

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return _NO_FLAGS
        return _NAME_FLAGS if index.column() == 0 else _CELL_FLAGS

    def data(self, index, role=_DISPLAY_ROLE):
        if not index.isValid():
            return None
        node: Node = index.internalPointer()
        if role == _DISPLAY_ROLE:
            column = index.column()
            if column == 0:
                return node.name
            if column == 1:
                if node.children is not None and node.files == 0:
                    return "—"
                return human_size(node.size)
            if node.children is not None:
                return node.path
            parent = node.parent
            if parent is None:
                return os.path.dirname(node.root_path)
            return parent.path
        if role == _DECORATION_ROLE:
            if index.column() != 0:
                return None
            if node.children is not None:
                return folder_icon()
            return file_icon(node.name)
        if role == _CHECK_ROLE:
            if index.column() != 0:
                return None
            checked = node.checked_units
            if checked == 0:
                return _UNCHECKED
            return _CHECKED if checked == node.units else _PARTIAL
        if role == _ALIGN_ROLE:
            return _RIGHT_ALIGN if index.column() == 1 else None
        if role == _TOOLTIP_ROLE:
            if node.children is not None:
                return (
                    f"{node.path}\n{node.files} файл(ов) · "
                    f"{human_size(node.size)}"
                )
            return node.path
        return None

    def setData(self, index, value, role=_CHECK_ROLE) -> bool:
        if role != _CHECK_ROLE or not index.isValid():
            return False
        started = time.perf_counter()
        node: Node = index.internalPointer()
        checked = Qt.CheckState(value) == Qt.CheckState.Checked
        set_checked(node, checked)
        self._notify_path(node)
        if node.children:
            self.subtree_checked.emit(self.index_for(node))
        self.selection_changed.emit()
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "Check toggled: %s checked=%s files=%d took %.1f ms",
                node.path, checked, node.files,
                (time.perf_counter() - started) * 1000,
            )
        return True

    def set_all_checked(self, checked: bool) -> None:
        if not self._roots:
            return
        for row, node in enumerate(self._roots):
            set_checked(node, checked)
            top = self.createIndex(row, 0, node)
            self.dataChanged.emit(top, top, _CHECK_ROLES)
            if node.children:
                self.subtree_checked.emit(top)
        self.selection_changed.emit()
        log.debug("All roots set checked=%s (%d roots)", checked,
                  len(self._roots))

    def add_root(self, node: Node) -> QModelIndex:
        row = len(self._roots)
        self.beginInsertRows(QModelIndex(), row, row)
        node.parent = None
        node.row = row
        self._roots.append(node)
        self.endInsertRows()
        self.selection_changed.emit()
        return self.index(row, 0, QModelIndex())

    def find_root(self, path: str) -> int:
        target = path.rstrip("\\/").lower()
        for row, node in enumerate(self._roots):
            if node.root_path.rstrip("\\/").lower() == target:
                return row
        return -1

    def remove_root(self, row: int) -> None:
        if not 0 <= row < len(self._roots):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        self._roots.pop(row)
        for position in range(row, len(self._roots)):
            self._roots[position].row = position
        self.endRemoveRows()
        self.selection_changed.emit()

    def remove_indexes(self, indexes) -> int:
        selected: dict[int, Node] = {}
        for index in indexes:
            if index.isValid():
                node = index.internalPointer()
                selected[id(node)] = node
        if not selected:
            return 0
        targets: list[Node] = []
        for node in selected.values():
            ancestor = node.parent
            while ancestor is not None and id(ancestor) not in selected:
                ancestor = ancestor.parent
            if ancestor is None:
                targets.append(node)
        groups: dict[int, list[Node]] = {}
        for node in targets:
            groups.setdefault(id(node.parent), []).append(node)
        for group in groups.values():
            group.sort(key=lambda item: item.row, reverse=True)
            for node in group:
                self._remove_node(node)
        self.selection_changed.emit()
        return len(targets)

    def _remove_node(self, node: Node) -> None:
        parent = node.parent
        if parent is None:
            self.remove_root(node.row)
            return
        children = parent.children or []
        row = node.row
        if row >= len(children) or children[row] is not node:
            log.warning("Stale row for %s (row=%d), skipping removal",
                        node.name, row)
            return
        self.beginRemoveRows(self.index_for(parent), row, row)
        children.pop(row)
        for position in range(row, len(children)):
            children[position].row = position
        self.endRemoveRows()
        self._recompute_ancestors(parent)

    def index_for(self, node: Node) -> QModelIndex:
        return self.createIndex(node.row, 0, node)

    def _recompute_ancestors(self, node: Node | None) -> None:
        while node is not None:
            children = node.children
            if children is None:
                break
            if not children:
                node.units = 1
                node.checked_units = 1
                node.files = node.checked_files = 0
                node.size = node.checked_size = 0
            else:
                units = checked_units = files = checked_files = 0
                size = checked_size = 0
                for child in children:
                    units += child.units
                    checked_units += child.checked_units
                    files += child.files
                    checked_files += child.checked_files
                    size += child.size
                    checked_size += child.checked_size
                node.units = units
                node.checked_units = checked_units
                node.files = files
                node.checked_files = checked_files
                node.size = size
                node.checked_size = checked_size
            self.dataChanged.emit(
                self.index_for(node),
                self.createIndex(node.row, _COLUMNS - 1, node),
            )
            node = node.parent

    def clear(self) -> None:
        if not self._roots:
            return
        self.beginResetModel()
        self._roots = []
        self.endResetModel()
        self.selection_changed.emit()

    # Only the toggled row and its ancestors are announced: one signal per
    # level instead of one per expanded subfolder, which made a click cost
    # O(expanded folders x visible rows) inside QTreeView. Descendant rows
    # read their state from the nodes, so the view only has to repaint them
    # (the window does it on subtree_checked).
    def _notify_path(self, node: Node | None) -> None:
        while node is not None:
            top = self.createIndex(node.row, 0, node)
            self.dataChanged.emit(top, top, _CHECK_ROLES)
            node = node.parent
