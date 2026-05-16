from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from typing import Callable, Iterable

_UNITS = ["Б", "КБ", "МБ", "ГБ", "ТБ"]


def human_size(num_bytes: int) -> str:
    value = float(max(0, num_bytes))
    idx = 0
    while value >= 1024.0 and idx < len(_UNITS) - 1:
        value /= 1024.0
        idx += 1
    unit = _UNITS[idx]
    if idx <= 1:
        return f"{round(value)} {unit}"
    rounded = round(value, 1)
    if rounded == int(rounded):
        text = str(int(rounded))
    else:
        text = f"{rounded:.1f}".replace(".", ",")
    return f"{text} {unit}"


def plural_files(n: int) -> str:
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return "файл"
    if 2 <= mod10 <= 4 and not (12 <= mod100 <= 14):
        return "файла"
    return "файлов"


@dataclass
class ArchiveItem:
    src: str
    arcname: str
    size: int = 0


def _unique_arcname(arcname: str, used: set[str]) -> str:
    if arcname not in used:
        used.add(arcname)
        return arcname
    root, ext = os.path.splitext(arcname)
    counter = 1
    while True:
        candidate = f"{root} ({counter}){ext}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def make_item(path: str) -> ArchiveItem:
    path = os.path.abspath(path)
    return ArchiveItem(src=path, arcname=os.path.basename(path),
                        size=_safe_size(path))


def make_items(paths: Iterable[str], base_dir: str) -> list[ArchiveItem]:
    base_dir = os.path.abspath(base_dir)
    out: list[ArchiveItem] = []
    for raw in paths:
        path = os.path.abspath(raw)
        try:
            arc = os.path.relpath(path, base_dir).replace(os.sep, "/")
        except ValueError:
            arc = os.path.basename(path)
        if arc.startswith(".."):
            arc = os.path.basename(path)
        out.append(ArchiveItem(src=path, arcname=arc, size=_safe_size(path)))
    return out


def expand_folder(folder: str) -> list[ArchiveItem]:
    folder = os.path.abspath(folder)
    base_parent = os.path.dirname(folder.rstrip(os.sep))
    items: list[ArchiveItem] = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            full = os.path.join(root, name)
            arcname = os.path.relpath(full, base_parent).replace(os.sep, "/")
            items.append(ArchiveItem(src=full, arcname=arcname,
                                      size=_safe_size(full)))
    return items


def create_zip(
    zip_path: str,
    items: Iterable[ArchiveItem],
    progress: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> int:
    items = list(items)
    total = sum(max(0, i.size) for i in items) or 1
    done = 0
    written = 0
    used: set[str] = set()

    try:
        with zipfile.ZipFile(
            zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as zf:
            for item in items:
                if should_cancel and should_cancel():
                    raise InterruptedError
                arcname = _unique_arcname(item.arcname, used)
                if progress:
                    progress(done, total, os.path.basename(item.src))
                try:
                    zf.write(item.src, arcname)
                    written += 1
                except (OSError, ValueError):
                    pass
                done += max(0, item.size)
                if progress:
                    progress(min(done, total), total,
                             os.path.basename(item.src))
    except InterruptedError:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass
        raise

    return written
