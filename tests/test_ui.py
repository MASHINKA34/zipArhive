from __future__ import annotations

import os
import time
import zipfile

import pytest
from conftest import write_file

from PyQt6.QtCore import QModelIndex, QPoint, Qt
from PyQt6.QtGui import QPixmap

from core.packer import PackOptions
from core.scanner import collect_items, scan_tree
from ui.file_model import FileTreeModel
from ui.icons import app_icon, file_icon, folder_icon, svg_pixmap
from ui.main_window import IDLE, MainWindow
from ui.widgets import MIXED
from ui.workers import PackWorker, ScanWorker

pytestmark = pytest.mark.usefixtures("qt_app")


def pump(app, predicate, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            app.processEvents()
            return True
        time.sleep(0.005)
    return False


def build_model(path) -> FileTreeModel:
    model = FileTreeModel()
    model.add_root(scan_tree(str(path)))
    return model


def find_row(model, parent, name):
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        if model.data(index) == name:
            return index
    raise AssertionError(f"нет строки {name}")


def test_model_structure(sample_tree):
    model = build_model(sample_tree)
    root_index = model.index(0, 0, QModelIndex())
    assert model.rowCount(QModelIndex()) == 1
    assert model.columnCount(QModelIndex()) == 3
    assert model.data(root_index) == "проект"
    assert model.data(root_index, Qt.ItemDataRole.CheckStateRole) == (
        Qt.CheckState.Checked
    )
    assert model.parent(root_index) == QModelIndex()

    source = find_row(model, root_index, "src")
    assert model.parent(source) == root_index
    assert model.rowCount(source) == 2
    assert model.hasChildren(source)

    main = find_row(model, source, "main.py")
    assert model.rowCount(main) == 0
    assert model.data(main.siblingAtColumn(2)) == os.path.join(
        str(sample_tree), "src"
    )
    assert model.data(main, Qt.ItemDataRole.ToolTipRole).endswith("main.py")
    assert model.data(main, Qt.ItemDataRole.DecorationRole) is not None


def test_model_check_toggle(sample_tree):
    model = build_model(sample_tree)
    changes = []
    model.selection_changed.connect(lambda: changes.append(1))
    root_index = model.index(0, 0, QModelIndex())
    source = find_row(model, root_index, "src")
    main = find_row(model, source, "main.py")

    assert model.setData(main, Qt.CheckState.Unchecked.value,
                         Qt.ItemDataRole.CheckStateRole)
    assert model.data(source, Qt.ItemDataRole.CheckStateRole) == (
        Qt.CheckState.PartiallyChecked
    )
    assert model.data(root_index, Qt.ItemDataRole.CheckStateRole) == (
        Qt.CheckState.PartiallyChecked
    )
    assert changes

    model.set_all_checked(False)
    assert model.roots[0].checked_units == 0
    model.set_all_checked(True)
    assert model.roots[0].checked_units == model.roots[0].units


def test_model_flags_and_headers(sample_tree):
    model = build_model(sample_tree)
    index = model.index(0, 0, QModelIndex())
    flags = model.flags(index)
    assert flags & Qt.ItemFlag.ItemIsUserCheckable
    assert not (model.flags(index.siblingAtColumn(1))
                & Qt.ItemFlag.ItemIsUserCheckable)
    assert model.flags(QModelIndex()) == Qt.ItemFlag.NoItemFlags
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Имя"
    assert model.headerData(2, Qt.Orientation.Horizontal) == "Путь"
    assert model.headerData(0, Qt.Orientation.Vertical) is None


def test_model_remove_and_clear(sample_tree):
    model = build_model(sample_tree)
    root_index = model.index(0, 0, QModelIndex())
    root_node = model.roots[0]
    before_files = root_node.files
    source = find_row(model, root_index, "src")
    removed_files = model.node_at(source).files

    model.remove_indexes([source])
    assert root_node.files == before_files - removed_files
    assert all(child.name != "src" for child in root_node.children)

    model.remove_indexes([model.index(0, 0, QModelIndex())])
    assert model.is_empty()
    model.clear()
    assert model.rowCount(QModelIndex()) == 0


def test_model_replaces_same_root(sample_tree):
    model = build_model(sample_tree)
    existing = model.find_root(str(sample_tree))
    assert existing == 0
    model.remove_root(existing)
    model.add_root(scan_tree(str(sample_tree)))
    assert model.rowCount(QModelIndex()) == 1
    assert model.find_root(str(sample_tree).upper()) == 0


def test_icons_render(qt_app):
    assert not app_icon().isNull()
    assert not folder_icon().isNull()
    assert not file_icon("photo.jpg").isNull()
    assert not file_icon("unknown.xyz").isNull()
    assert not file_icon("Makefile").isNull()
    assert not svg_pixmap("box", 44, "#ffffff").isNull()


def test_app_icon_fallback_without_asset(qt_app, monkeypatch):
    from ui import icons

    icons.app_icon.cache_clear()
    monkeypatch.setattr(icons, "asset_path", lambda *parts: "нет_файла.ico")
    icon = icons.app_icon()
    icons.app_icon.cache_clear()
    assert not icon.isNull()
    assert icon.availableSizes()
    assert not icon.pixmap(64, 64).isNull()


def test_window_scan_and_render(qt_app, sample_tree):
    window = MainWindow()
    window.resize(1000, 700)
    window.show()
    window.add_path(str(sample_tree))
    assert pump(qt_app, lambda: window._state == IDLE and
                not window.model.is_empty())

    assert window.model.rowCount(QModelIndex()) == 1
    assert window.stack.currentIndex() == 1
    assert window.select_all_box.state() is True

    window.view.expandAll()
    qt_app.processEvents()
    pixmap = QPixmap(window.view.size())
    window.view.render(pixmap)
    assert not pixmap.isNull()

    root_index = window.model.index(0, 0, QModelIndex())
    child = window.model.index(0, 0, root_index)
    window.model.setData(child, Qt.CheckState.Unchecked.value,
                         Qt.ItemDataRole.CheckStateRole)
    qt_app.processEvents()
    assert window.select_all_box.state() == MIXED

    window.model.set_all_checked(False)
    qt_app.processEvents()
    assert window.select_all_box.state() is False
    assert not window.bottom.pack_button.isEnabled()

    window.model.set_all_checked(True)
    qt_app.processEvents()
    assert window.bottom.pack_button.isEnabled()

    window._clear_all()
    assert window.stack.currentIndex() == 0
    window.close()


def test_window_add_single_file(qt_app, tmp_path):
    path = write_file(str(tmp_path / "one.txt"), b"hello")
    window = MainWindow()
    window.add_path(path)
    assert pump(qt_app, lambda: window._state == IDLE and
                not window.model.is_empty())
    assert window.model.roots[0].files == 1
    window.add_path(str(tmp_path / "missing.txt"))
    assert window.model.rowCount(QModelIndex()) == 1
    window.close()


def test_window_context_menu_and_shortcuts(qt_app, sample_tree):
    window = MainWindow()
    window.add_path(str(sample_tree))
    assert pump(qt_app, lambda: window._state == IDLE and
                not window.model.is_empty())
    root_index = window.model.index(0, 0, QModelIndex())
    window.view.selectionModel().select(
        root_index,
        window.view.selectionModel().SelectionFlag.Select
        | window.view.selectionModel().SelectionFlag.Rows,
    )
    window._remove_selected()
    assert window.model.is_empty()
    window.close()


def test_window_drop_paths(qt_app, sample_tree):
    from PyQt6.QtCore import QMimeData, QUrl
    from PyQt6.QtGui import QDropEvent

    window = MainWindow()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(sample_tree))])
    event = QDropEvent(
        QPoint(10, 10).toPointF(),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dropEvent(event)
    assert pump(qt_app, lambda: window._state == IDLE and
                not window.model.is_empty())
    assert window.model.roots[0].name == "проект"
    window.close()


def test_scan_worker_signals(qt_app, sample_tree):
    worker = ScanWorker(str(sample_tree))
    result = {}
    worker.scanned.connect(lambda node: result.update(node=node))
    worker.start()
    assert pump(qt_app, lambda: worker.isFinished() and "node" in result)
    assert result["node"].files == 6


def test_pack_worker_full_cycle(qt_app, sample_tree, tmp_path):
    root = scan_tree(str(sample_tree))
    items = collect_items([root])
    target = str(tmp_path / "ui.zip")
    worker = PackWorker(target, items, PackOptions(level=1))
    events = {"progress": [], "result": None}
    worker.progress.connect(
        lambda done, total, name: events["progress"].append(done)
    )
    worker.packed.connect(lambda result: events.update(result=result))
    worker.start()
    assert pump(qt_app, lambda: worker.isFinished()
                and events["result"] is not None)
    result = events["result"]
    assert result.written == len(items)
    assert not result.cancelled
    assert events["progress"]
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(items)


def test_pack_worker_cancel(qt_app, tmp_path):
    for index in range(60):
        write_file(str(tmp_path / "data" / f"f{index}.txt"), b"x" * 200000)
    root = scan_tree(str(tmp_path / "data"))
    target = str(tmp_path / "cancel.zip")
    worker = PackWorker(target, collect_items([root]),
                        PackOptions(level=9, workers=1))
    done = {}
    worker.packed.connect(lambda result: done.update(result=result))
    worker.start()
    worker.cancel()
    assert pump(qt_app, lambda: worker.isFinished() and "result" in done)
    assert done["result"].cancelled
    assert not os.path.exists(target)


def test_window_pack_flow(qt_app, sample_tree, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    target = str(tmp_path / "через_окно.zip")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (target, "")),
    )
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)

    window = MainWindow()
    window.add_path(str(sample_tree))
    assert pump(qt_app, lambda: window._state == IDLE
                and not window.model.is_empty())

    window._start_pack()
    assert pump(qt_app, lambda: window._state == IDLE
                and os.path.exists(target))
    assert window.bottom.pack_button.isVisible() or window.isHidden()
    assert "Готово" in window.status.left.text()
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert any(
            name.endswith("src/main.py") for name in archive.namelist()
        )
    window.close()


def test_window_close_while_scanning(qt_app, sample_tree):
    window = MainWindow()
    window.add_path(str(sample_tree))
    window.close()
    assert pump(qt_app, lambda: window._scanner is None
                or not window._scanner.isRunning())
