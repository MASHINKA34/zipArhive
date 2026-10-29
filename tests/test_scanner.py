from __future__ import annotations

import os
import zipfile

import pytest
from conftest import write_file

from core.packer import create_zip
from core.scanner import (
    CHECKED,
    PARTIAL,
    UNCHECKED,
    ScanCancelled,
    collect_items,
    scan_file,
    scan_tree,
    set_checked,
    summary,
)


def child_named(node, name):
    for child in node.children or []:
        if child.name == name:
            return child
    raise AssertionError(f"нет узла {name}")


def test_scan_counts_and_sizes(sample_tree):
    root = scan_tree(str(sample_tree))
    assert root.name == "проект"
    assert root.files == 6
    assert root.size == sum(
        os.path.getsize(os.path.join(base, name))
        for base, _dirs, files in os.walk(str(sample_tree))
        for name in files
    )
    assert root.state() == CHECKED


def test_scan_orders_directories_first(sample_tree):
    root = scan_tree(str(sample_tree))
    names = [child.name for child in root.children]
    directories = [child.name for child in root.children if child.is_dir]
    assert names[:len(directories)] == directories
    assert directories == sorted(directories, key=str.lower)


def test_scan_keeps_empty_directory(sample_tree):
    root = scan_tree(str(sample_tree))
    empty = child_named(root, "пустая_папка")
    assert empty.is_dir
    assert empty.children == []
    assert empty.units == 1
    assert empty.files == 0


def test_scan_progress_and_cancel(tmp_path):
    for index in range(20):
        write_file(str(tmp_path / f"dir{index}" / "file.txt"), b"x" * 100)
    seen = []
    root = scan_tree(str(tmp_path), on_progress=lambda f, b: seen.append(f))
    assert root.files == 20
    assert seen and seen[-1] == 20

    with pytest.raises(ScanCancelled):
        scan_tree(str(tmp_path), should_cancel=lambda: True)


def test_scan_missing_directory_returns_empty_root(tmp_path):
    root = scan_tree(str(tmp_path / "нет_такой"))
    assert root.files == 0
    assert root.children == []


def test_scan_logs_unreadable_directory_and_summary(tmp_path, caplog):
    missing = tmp_path / "нет_такой"
    with caplog.at_level("INFO", logger="quickzip.scanner"):
        scan_tree(str(missing))
    messages = [record.getMessage() for record in caplog.records]
    assert any("Cannot list directory" in text and "нет_такой" in text
               for text in messages)
    assert any(text.startswith("Scanned ") and "1 unreadable" in text
               for text in messages)


def test_scan_file(tmp_path):
    path = write_file(str(tmp_path / "one.txt"), b"12345")
    node = scan_file(path)
    assert node is not None
    assert node.files == 1
    assert node.size == 5
    assert not node.is_dir
    assert scan_file(str(tmp_path / "нет.txt")) is None


def test_node_path_resolution(sample_tree):
    root = scan_tree(str(sample_tree))
    source = child_named(root, "src")
    main = child_named(source, "main.py")
    assert main.path == os.path.join(str(sample_tree), "src", "main.py")


def test_check_state_propagation(sample_tree):
    root = scan_tree(str(sample_tree))
    source = child_named(root, "src")
    main = child_named(source, "main.py")

    set_checked(main, False)
    assert main.state() == UNCHECKED
    assert source.state() == PARTIAL
    assert root.state() == PARTIAL
    assert root.checked_files == root.files - 1
    assert root.checked_size == root.size - main.size

    set_checked(main, True)
    assert root.state() == CHECKED
    assert root.checked_size == root.size

    set_checked(root, False)
    assert root.checked_units == 0
    assert main.state() == UNCHECKED
    assert summary([root]) == (root.files, 0, root.size, 0)


def test_collect_items_paths_and_order(sample_tree):
    root = scan_tree(str(sample_tree))
    items = collect_items([root])
    names = [item.arcname for item in items]
    assert names[0].startswith("проект/")
    assert "проект/src/main.py" in names
    assert "проект/пустая_папка" in names
    for item in items:
        if not item.is_dir:
            assert os.path.isfile(item.src)
            assert item.size == os.path.getsize(item.src)


def test_collect_items_respects_selection(sample_tree):
    root = scan_tree(str(sample_tree))
    assets = child_named(root, "assets")
    set_checked(assets, False)
    names = [item.arcname for item in collect_items([root])]
    assert not any(name.startswith("проект/assets") for name in names)
    assert "проект/readme.md" in names


@pytest.mark.skipif(os.name != "nt", reason="проверка длинных путей Windows")
def test_long_windows_path(tmp_path):
    from core.fsutil import long_path

    deep = str(tmp_path)
    for index in range(10):
        deep = os.path.join(deep, f"очень_длинное_имя_каталога_{index:02d}")
    os.makedirs(long_path(deep), exist_ok=True)
    payload = b"long path payload" * 64
    target_file = os.path.join(deep, "файл.txt")
    with open(long_path(target_file), "wb") as handle:
        handle.write(payload)
    assert len(target_file) > 260

    root = scan_tree(str(tmp_path))
    items = collect_items([root])
    assert root.files == 1
    archive_path = os.path.join(str(tmp_path), "long.zip")
    result = create_zip(archive_path, items)
    assert result.written == len(items)
    assert result.skipped == 0
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.read(items[0].arcname) == payload


def test_scan_to_archive_roundtrip(sample_tree, tmp_path):
    root = scan_tree(str(sample_tree))
    target = str(tmp_path / "tree.zip")
    result = create_zip(target, collect_items([root]))
    assert result.skipped == 0
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            disk = os.path.join(
                str(sample_tree.parent), name.replace("/", os.sep)
            )
            with open(disk, "rb") as handle:
                assert archive.read(name) == handle.read()
