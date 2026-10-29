from __future__ import annotations

import logging
import os
import time
from typing import Callable, Iterable

from core.formatting import natural_key
from core.fsutil import long_path
from core.packer import ArchiveItem

UNCHECKED = 0
PARTIAL = 1
CHECKED = 2

PROGRESS_STEP = 4096

log = logging.getLogger("quickzip.scanner")


class Node:
    __slots__ = (
        "name", "parent", "row", "children", "root_path",
        "size", "mtime", "units", "checked_units",
        "files", "checked_files", "checked_size",
    )

    def __init__(self, name: str, parent: "Node | None", row: int) -> None:
        self.name = name
        self.parent = parent
        self.row = row
        self.children: list[Node] | None = None
        self.root_path = ""
        self.size = 0
        self.mtime = 0.0
        self.units = 1
        self.checked_units = 1
        self.files = 0
        self.checked_files = 0
        self.checked_size = 0

    @property
    def is_dir(self) -> bool:
        return self.children is not None

    @property
    def path(self) -> str:
        node = self
        parts: list[str] = []
        while node.parent is not None:
            parts.append(node.name)
            node = node.parent
        if not parts:
            return node.root_path
        parts.append(node.root_path)
        parts.reverse()
        return os.path.join(*parts)

    def state(self) -> int:
        if self.checked_units == 0:
            return UNCHECKED
        if self.checked_units == self.units:
            return CHECKED
        return PARTIAL


class ScanCancelled(Exception):
    pass


def scan_tree(
    root_path: str,
    on_progress: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> Node:
    started = time.perf_counter()
    root_path = os.path.abspath(root_path)
    log.debug("Scanning tree %s", root_path)
    root = Node(os.path.basename(root_path) or root_path, None, 0)
    root.root_path = root_path
    root.children = []
    queue: list[tuple[Node, str]] = [(root, root_path)]
    directories: list[Node] = [root]
    index = 0
    seen_files = 0
    seen_bytes = 0
    unreadable = 0
    next_report = PROGRESS_STEP
    debug = log.isEnabledFor(logging.DEBUG)

    while index < len(queue):
        node, current = queue[index]
        index += 1
        if should_cancel is not None and should_cancel():
            log.info(
                "Scan of %s cancelled after %d files in %.0f ms",
                root_path, seen_files, (time.perf_counter() - started) * 1000,
            )
            raise ScanCancelled
        try:
            with os.scandir(long_path(current)) as iterator:
                entries = list(iterator)
        except OSError as exc:
            unreadable += 1
            log.warning("Cannot list directory %s: %s", current, exc)
            continue
        dir_entries: list[os.DirEntry] = []
        file_entries: list[tuple[str, int, float]] = []
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    dir_entries.append(entry)
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    file_entries.append((entry.name, stat.st_size,
                                         stat.st_mtime))
            except OSError as exc:
                unreadable += 1
                log.warning("Cannot stat %s: %s", entry.path, exc)
                continue
        dir_entries.sort(key=lambda item: natural_key(item.name))
        file_entries.sort(key=lambda item: natural_key(item[0]))

        children: list[Node] = []
        for entry in dir_entries:
            child = Node(entry.name, node, len(children))
            child.children = []
            children.append(child)
            queue.append((child, os.path.join(current, entry.name)))
            directories.append(child)
        for name, size, mtime in file_entries:
            child = Node(name, node, len(children))
            child.size = size
            child.checked_size = size
            child.mtime = mtime
            child.files = 1
            child.checked_files = 1
            children.append(child)
            seen_files += 1
            seen_bytes += size
        node.children = children
        if debug:
            log.debug("Listed %s: %d dirs, %d files", current,
                      len(dir_entries), len(file_entries))

        if on_progress is not None and seen_files >= next_report:
            next_report = seen_files + PROGRESS_STEP
            on_progress(seen_files, seen_bytes)

    for node in reversed(directories):
        children = node.children or []
        if not children:
            node.units = 1
            node.checked_units = 1
            continue
        units = files = 0
        size = 0
        for child in children:
            units += child.units
            files += child.files
            size += child.size
        node.units = units
        node.checked_units = units
        node.files = files
        node.checked_files = files
        node.size = size
        node.checked_size = size

    if on_progress is not None:
        on_progress(seen_files, seen_bytes)
    log.info(
        "Scanned %s: %d dirs, %d files, %d bytes, %d unreadable in %.0f ms",
        root_path, len(directories), seen_files, seen_bytes, unreadable,
        (time.perf_counter() - started) * 1000,
    )
    return root


def scan_file(path: str) -> Node | None:
    path = os.path.abspath(path)
    try:
        stat = os.stat(long_path(path))
    except OSError as exc:
        log.warning("Cannot stat file %s: %s", path, exc)
        return None
    node = Node(os.path.basename(path) or path, None, 0)
    node.root_path = path
    node.size = stat.st_size
    node.checked_size = stat.st_size
    node.mtime = stat.st_mtime
    node.files = 1
    node.checked_files = 1
    return node


def set_checked(node: Node, checked: bool) -> None:
    target_units = node.units if checked else 0
    target_files = node.files if checked else 0
    target_size = node.size if checked else 0
    delta_units = target_units - node.checked_units
    delta_files = target_files - node.checked_files
    delta_size = target_size - node.checked_size
    if delta_units == 0 and delta_files == 0 and delta_size == 0:
        return
    _apply_subtree(node, checked)
    parent = node.parent
    while parent is not None:
        parent.checked_units += delta_units
        parent.checked_files += delta_files
        parent.checked_size += delta_size
        parent = parent.parent


def _apply_subtree(node: Node, checked: bool) -> None:
    stack = [node]
    while stack:
        current = stack.pop()
        current.checked_units = current.units if checked else 0
        current.checked_files = current.files if checked else 0
        current.checked_size = current.size if checked else 0
        if current.children:
            stack.extend(current.children)


def collect_items(roots: Iterable[Node]) -> list[ArchiveItem]:
    items: list[ArchiveItem] = []
    stack: list[tuple[Node, str, str]] = [
        (root, root.name, root.root_path)
        for root in roots if root.checked_units
    ]
    stack.reverse()
    join = os.path.join
    while stack:
        node, arcname, path = stack.pop()
        children = node.children
        if children is None:
            items.append(ArchiveItem(path, arcname, node.size, node.mtime))
            continue
        if not children:
            items.append(ArchiveItem(path, arcname, 0, node.mtime, True))
            continue
        for child in reversed(children):
            if child.checked_units:
                stack.append(
                    (child, f"{arcname}/{child.name}", join(path, child.name))
                )
    return items


def summary(roots: Iterable[Node]) -> tuple[int, int, int, int]:
    files = checked_files = 0
    size = checked_size = 0
    for root in roots:
        files += root.files
        checked_files += root.checked_files
        size += root.size
        checked_size += root.checked_size
    return files, checked_files, size, checked_size
