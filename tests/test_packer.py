from __future__ import annotations

import os
import zipfile
import zlib

import pytest
from conftest import random_blob, text_blob, write_file

from core.packer import (
    ArchiveItem,
    PackOptions,
    STORE_EXTENSIONS,
    create_zip,
    crc32_combine,
    default_workers,
    extension_of,
)
from core.zipwriter import DEFLATED, STORED


def items_from(root, names):
    result = []
    for name in names:
        path = os.path.join(str(root), name.replace("/", os.sep))
        result.append(
            ArchiveItem(path, name, os.path.getsize(path),
                        os.path.getmtime(path))
        )
    return result


def read_back(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        return {
            info.filename: archive.read(info.filename)
            for info in archive.infolist()
        }


def test_extension_of():
    assert extension_of("a/b/photo.JPG") == "jpg"
    assert extension_of("archive.tar.gz") == "gz"
    assert extension_of("Makefile") == ""
    assert extension_of(".gitignore") == ""


def test_crc32_combine_matches_zlib():
    left = b"quick zip " * 37
    right = b"parallel deflate" * 11
    combined = crc32_combine(zlib.crc32(left), zlib.crc32(right), len(right))
    assert combined == zlib.crc32(left + right)


def test_crc32_combine_zero_length():
    assert crc32_combine(0x1234, 0, 0) == 0x1234


@pytest.mark.parametrize("length", [1, 2, 7, 64, 4095, 65537, 4 << 20])
def test_crc32_combine_matches_zlib_on_many_lengths(length):
    left = random_blob(1000, length)
    right = random_blob(length, length + 1)
    combined = crc32_combine(zlib.crc32(left), zlib.crc32(right), len(right))
    assert combined == zlib.crc32(left + right)


def test_pack_logs_summary_and_skipped_files(tmp_path, caplog):
    write_file(str(tmp_path / "src" / "ok.txt"), text_blob(5000))
    items = items_from(tmp_path / "src", ["ok.txt"])
    items.append(ArchiveItem(str(tmp_path / "src" / "gone.txt"), "gone.txt",
                             10, 0.0))
    target = str(tmp_path / "log.zip")
    with caplog.at_level("INFO", logger="quickzip.packer"):
        result = create_zip(target, items, PackOptions(workers=2))
    assert result.skipped == 1
    messages = [record.getMessage() for record in caplog.records]
    assert any("Skipped unreadable file" in text and "gone.txt" in text
               for text in messages)
    assert any(text.startswith("Archive written") for text in messages)


def test_roundtrip_small_files(tmp_path):
    payloads = {
        "docs/readme.md": text_blob(3000),
        "docs/раздел/заметка.txt": "привет мир".encode() * 40,
        "empty.bin": b"",
        "data/blob.dat": random_blob(60000, 5),
    }
    for name, data in payloads.items():
        write_file(os.path.join(str(tmp_path), name.replace("/", os.sep)),
                   data)
    target = str(tmp_path / "out.zip")
    result = create_zip(target, items_from(tmp_path, payloads))
    assert result.written == len(payloads)
    assert result.skipped == 0
    assert not result.cancelled
    assert read_back(target) == payloads


def test_directory_entries(tmp_path):
    write_file(str(tmp_path / "a" / "file.txt"), b"data")
    items = [
        ArchiveItem(str(tmp_path / "empty"), "root/empty", 0, 0.0, True),
        ArchiveItem(str(tmp_path / "a" / "file.txt"), "root/a/file.txt", 4),
    ]
    target = str(tmp_path / "dirs.zip")
    create_zip(target, items)
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
    assert "root/empty/" in names
    assert "root/a/file.txt" in names


def test_smart_store_keeps_media_uncompressed(tmp_path):
    write_file(str(tmp_path / "clip.mp4"), random_blob(200000, 3))
    write_file(str(tmp_path / "notes.txt"), text_blob(200000, 4))
    target = str(tmp_path / "mixed.zip")
    create_zip(target, items_from(tmp_path, ["clip.mp4", "notes.txt"]))
    with zipfile.ZipFile(target) as archive:
        assert archive.getinfo("clip.mp4").compress_type == STORED
        assert archive.getinfo("notes.txt").compress_type == DEFLATED


def test_smart_store_can_be_disabled(tmp_path):
    write_file(str(tmp_path / "clip.mp4"), text_blob(120000, 8))
    target = str(tmp_path / "forced.zip")
    create_zip(target, items_from(tmp_path, ["clip.mp4"]),
               PackOptions(smart_store=False))
    with zipfile.ZipFile(target) as archive:
        assert archive.getinfo("clip.mp4").compress_type == DEFLATED


def test_incompressible_data_falls_back_to_store(tmp_path):
    write_file(str(tmp_path / "noise.bin"), random_blob(120000, 21))
    target = str(tmp_path / "noise.zip")
    create_zip(target, items_from(tmp_path, ["noise.bin"]))
    with zipfile.ZipFile(target) as archive:
        info = archive.getinfo("noise.bin")
    assert info.compress_type == STORED
    assert info.compress_size == 120000


@pytest.mark.parametrize("level", [1, 6, 9])
def test_large_file_chunked_paths(tmp_path, level):
    payload = text_blob(5 << 20, 17)
    write_file(str(tmp_path / "big.log"), payload)
    target = str(tmp_path / f"big{level}.zip")
    options = PackOptions(
        level=level, chunk_size=256 << 10, inline_limit=512 << 10
    )
    result = create_zip(target, items_from(tmp_path, ["big.log"]), options)
    assert result.written == 1
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        info = archive.getinfo("big.log")
        assert info.file_size == len(payload)
        assert info.CRC == zlib.crc32(payload)
        assert archive.read("big.log") == payload
        assert info.compress_size < info.file_size


def test_large_stored_file_chunked(tmp_path):
    payload = random_blob(3 << 20, 23)
    write_file(str(tmp_path / "movie.mp4"), payload)
    target = str(tmp_path / "movie.zip")
    options = PackOptions(chunk_size=256 << 10, inline_limit=512 << 10)
    create_zip(target, items_from(tmp_path, ["movie.mp4"]), options)
    with zipfile.ZipFile(target) as archive:
        assert archive.getinfo("movie.mp4").compress_type == STORED
        assert archive.read("movie.mp4") == payload


def test_duplicate_arcnames_are_renamed(tmp_path):
    write_file(str(tmp_path / "one" / "note.txt"), b"first")
    write_file(str(tmp_path / "two" / "note.txt"), b"second")
    items = [
        ArchiveItem(str(tmp_path / "one" / "note.txt"), "note.txt", 5),
        ArchiveItem(str(tmp_path / "two" / "note.txt"), "note.txt", 6),
    ]
    target = str(tmp_path / "dupes.zip")
    create_zip(target, items)
    content = read_back(target)
    assert content == {"note.txt": b"first", "note (1).txt": b"second"}


def test_missing_file_is_skipped(tmp_path):
    write_file(str(tmp_path / "ok.txt"), b"payload")
    items = [
        ArchiveItem(str(tmp_path / "ok.txt"), "ok.txt", 7),
        ArchiveItem(str(tmp_path / "gone.txt"), "gone.txt", 10),
    ]
    target = str(tmp_path / "partial.zip")
    result = create_zip(target, items)
    assert result.written == 1
    assert result.skipped == 1
    assert result.warnings
    assert read_back(target) == {"ok.txt": b"payload"}


def test_cancel_removes_archive(tmp_path):
    for index in range(40):
        write_file(str(tmp_path / f"file_{index}.txt"), text_blob(50000,
                                                                  index))
    names = [f"file_{index}.txt" for index in range(40)]
    target = str(tmp_path / "cancelled.zip")
    calls = {"count": 0}

    def cancel():
        calls["count"] += 1
        return calls["count"] > 2

    result = create_zip(target, items_from(tmp_path, names),
                        PackOptions(workers=2), should_cancel=cancel)
    assert result.cancelled
    assert not os.path.exists(target)


def test_progress_is_monotonic(tmp_path):
    names = []
    for index in range(12):
        name = f"chunk_{index}.txt"
        write_file(str(tmp_path / name), text_blob(120000, index))
        names.append(name)
    seen: list[int] = []
    target = str(tmp_path / "progress.zip")
    result = create_zip(
        target, items_from(tmp_path, names),
        PackOptions(progress_interval=0.0),
        progress=lambda done, total, name: seen.append(done),
    )
    assert seen
    assert seen == sorted(seen)
    assert seen[-1] == result.total_size


def test_empty_item_list(tmp_path):
    target = str(tmp_path / "empty.zip")
    result = create_zip(target, [])
    assert result.written == 0
    with zipfile.ZipFile(target) as archive:
        assert archive.namelist() == []


def test_worker_counts_produce_identical_output(tmp_path):
    names = []
    for index in range(30):
        name = f"src/mod_{index}.py"
        write_file(os.path.join(str(tmp_path), name.replace("/", os.sep)),
                   text_blob(40000, index))
        names.append(name)
    items = items_from(tmp_path, names)
    single = str(tmp_path / "single.zip")
    parallel = str(tmp_path / "parallel.zip")
    create_zip(single, items, PackOptions(workers=1))
    create_zip(parallel, items, PackOptions(workers=8))
    with open(single, "rb") as left, open(parallel, "rb") as right:
        assert left.read() == right.read()


def test_default_workers_within_bounds():
    assert 2 <= default_workers() <= 16


def test_store_extensions_are_lowercase():
    assert all(name == name.lower() for name in STORE_EXTENSIONS)


def test_archive_is_readable_by_shell(tmp_path):
    write_file(str(tmp_path / "текст.txt"), "данные".encode() * 100)
    target = str(tmp_path / "unicode.zip")
    create_zip(target, items_from(tmp_path, ["текст.txt"]))
    with zipfile.ZipFile(target) as archive:
        info = archive.infolist()[0]
        assert info.flag_bits & 0x800
        assert info.filename == "текст.txt"
