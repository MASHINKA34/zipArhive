from __future__ import annotations

import os

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSignal

from core.formatting import human_size
from core.scanner import CHECKED, PARTIAL, Node, set_checked
from ui.icons import file_icon, folder_icon

_CHECK_ROLE = Qt.ItemDataRole.CheckStateRole
_DISPLAY_ROLE = Qt.ItemDataRole.DisplayRole
_STATE_MAP = {
    CHECKED: Qt.CheckState.Checked,
    PARTIAL: Qt.CheckState.PartiallyChecked,
}


class FileTreeModel(QAbstractItemModel):
    selection_changed = pyqtSignal()

    HEADERS = ("Имя", "Размер", "Путь")

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

    def index(self, row, column, parent=QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if parent.isValid():
            children = parent.internalPointer().children or []
        else:
            children = self._roots
        if row >= len(children):
            return QModelIndex()
        return self.createIndex(row, column, children[row])

    def parent(self, index=QModelIndex()) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        parent = index.internalPointer().parent
        if parent is None:
            return QModelIndex()
        return self.createIndex(parent.row, 0, parent)

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            return len(self._roots)
        children = parent.internalPointer().children
        return len(children) if children else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def hasChildren(self, parent=QModelIndex()) -> bool:
        if not parent.isValid():
            return bool(self._roots)
        return bool(parent.internalPointer().children)

    def headerData(self, section, orientation, role=_DISPLAY_ROLE):
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == _DISPLAY_ROLE and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole and section == 1:
            return int(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        return None

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        if index.column() == 0:
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index, role=_DISPLAY_ROLE):
        if not index.isValid():
            return None
        node: Node = index.internalPointer()
        column = index.column()
        if role == _DISPLAY_ROLE:
            if column == 0:
                return node.name
            if column == 1:
                if node.is_dir and node.files == 0:
                    return "—"
                return human_size(node.size)
            path = node.path
            return path if node.is_dir else os.path.dirname(path)
        if role == Qt.ItemDataRole.DecorationRole and column == 0:
            return folder_icon() if node.is_dir else file_icon(node.name)
        if role == _CHECK_ROLE and column == 0:
            return _STATE_MAP.get(node.state(), Qt.CheckState.Unchecked)
        if role == Qt.ItemDataRole.TextAlignmentRole and column == 1:
            return int(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        if role == Qt.ItemDataRole.ToolTipRole:
            if node.is_dir:
                return f"{node.path}\n{node.files} файл(ов) · {human_size(node.size)}"
            return node.path
        return None

    def setData(self, index, value, role=_CHECK_ROLE) -> bool:
        if role != _CHECK_ROLE or not index.isValid():
            return False
        node: Node = index.internalPointer()
        checked = Qt.CheckState(value) == Qt.CheckState.Checked
        set_checked(node, checked)
        self._notify_subtree(index)
        self._notify_ancestors(index)
        self.selection_changed.emit()
        return True

    def set_all_checked(self, checked: bool) -> None:
        if not self._roots:
            return
        for node in self._roots:
            set_checked(node, checked)
        for row in range(len(self._roots)):
            self._notify_subtree(self.index(row, 0, QModelIndex()))
        self.selection_changed.emit()

    def set_expanded(self, index: QModelIndex, expanded: bool) -> None:
        node = self.node_at(index)
        if node is not None:
            node.expanded = expanded

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

    def remove_indexes(self, indexes) -> None:
        selected: dict[int, Node] = {}
        for index in indexes:
            if index.isValid():
                node = index.internalPointer()
                selected[id(node)] = node
        if not selected:
            return
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

    def _remove_node(self, node: Node) -> None:
        parent = node.parent
        if parent is None:
            self.remove_root(node.row)
            return
        children = parent.children or []
        row = node.row
        if row >= len(children) or children[row] is not node:
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
            index = self.index_for(node)
            self.dataChanged.emit(
                index, index.siblingAtColumn(self.columnCount() - 1)
            )
            node = node.parent

    def clear(self) -> None:
        if not self._roots:
            return
        self.beginResetModel()
        self._roots = []
        self.endResetModel()
        self.selection_changed.emit()

    def _notify_subtree(self, index: QModelIndex) -> None:
        node: Node = index.internalPointer()
        last = index.siblingAtColumn(self.columnCount() - 1)
        self.dataChanged.emit(index, last, [_CHECK_ROLE])
        children = node.children
        if not children or not node.expanded:
            return
        self.dataChanged.emit(
            self.index(0, 0, index),
            self.index(len(children) - 1, self.columnCount() - 1, index),
            [_CHECK_ROLE],
        )
        for row, child in enumerate(children):
            if child.children and child.expanded:
                self._notify_subtree(self.index(row, 0, index))

    def _notify_ancestors(self, index: QModelIndex) -> None:
        parent = index.parent()
        while parent.isValid():
            self.dataChanged.emit(
                parent,
                parent.siblingAtColumn(self.columnCount() - 1),
                [_CHECK_ROLE],
            )
            parent = parent.parent()
