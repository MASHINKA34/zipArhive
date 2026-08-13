from __future__ import annotations

import io
import time
import zipfile
import zlib

import pytest

from core.zipwriter import (
    DEFLATED,
    STORED,
    ZipWriter,
    dos_timestamp,
    encode_name,
)


def build(callback) -> bytes:
    buffer = io.BytesIO()
    writer = ZipWriter(buffer)
    callback(writer)
    size = writer.finish()
    data = buffer.getvalue()
    assert size == len(data)
    return data


def test_encode_name_normalizes_separators():
    assert encode_name("a\\b\\c.txt", False) == (b"a/b/c.txt", 0)
    assert encode_name("/leading.txt", False) == (b"leading.txt", 0)
    assert encode_name("a//b.txt", False) == (b"a/b.txt", 0)
    assert encode_name("dir", True) == (b"dir/", 0)
    assert encode_name("dir/", True) == (b"dir/", 0)


def test_encode_name_sets_utf8_flag():
    name, flag = encode_name("папка/файл.txt", False)
    assert name == "папка/файл.txt".encode("utf-8")
    assert flag == 0x0800


@pytest.mark.parametrize(
    "moment,expected_date",
    [
        (0.0, (0 << 9) | (1 << 5) | 1),
        (time.mktime((2024, 5, 17, 12, 30, 20, 0, 1, -1)),
         ((2024 - 1980) << 9) | (5 << 5) | 17),
    ],
)
def test_dos_timestamp(moment, expected_date):
    _dos_time, dos_date = dos_timestamp(moment)
    assert dos_date == expected_date


def test_dos_timestamp_handles_broken_values():
    epoch_date = (1 << 5) | 1
    assert dos_timestamp(-(10 ** 12)) == (0, epoch_date)
    assert dos_timestamp(10 ** 12) == (0, epoch_date)
    far_future = time.mktime((2200, 6, 15, 10, 0, 0, 0, 1, -1))
    assert dos_timestamp(far_future)[1] == (
        ((2107 - 1980) << 9) | (12 << 5) | 31
    )


def test_stored_and_deflated_entries():
    payload = b"quick zip " * 500
    packed = zlib.compressobj(6, zlib.DEFLATED, -15)
    compressed = packed.compress(payload) + packed.flush()

    def fill(writer: ZipWriter) -> None:
        writer.add_blob("raw.bin", payload, zlib.crc32(payload),
                        len(payload), STORED)
        writer.add_blob("packed.bin", compressed, zlib.crc32(payload),
                        len(payload), DEFLATED)
        writer.add_directory("папка")

    data = build(fill)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == ["raw.bin", "packed.bin", "папка/"]
        assert archive.read("raw.bin") == payload
        assert archive.read("packed.bin") == payload
        info = archive.getinfo("папка/")
        assert info.is_dir()
        assert info.external_attr & 0x10


def test_stream_entry_uses_data_descriptor():
    payload = b"stream payload " * 400
    compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
    first = compressor.compress(payload) + compressor.flush(
        zlib.Z_FULL_FLUSH
    )
    tail = zlib.compressobj(6, zlib.DEFLATED, -15)
    second = tail.compress(payload) + tail.flush(zlib.Z_FINISH)

    def fill(writer: ZipWriter) -> None:
        writer.open_stream("big.log", DEFLATED, len(payload) * 2)
        writer.write_stream(first)
        writer.write_stream(second)
        writer.close_stream(
            zlib.crc32(payload * 2), len(first) + len(second), len(payload) * 2
        )

    data = build(fill)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.getinfo("big.log")
        assert info.flag_bits & 0x08
        assert archive.read("big.log") == payload * 2
        assert archive.testzip() is None


def test_zip64_stream_entry_is_readable():
    payload = b"z" * 1000

    def fill(writer: ZipWriter) -> None:
        entry = writer.open_stream("huge.bin", STORED, 5 << 30)
        assert entry.zip64
        writer.write_stream(payload)
        writer.close_stream(zlib.crc32(payload), len(payload), len(payload))

    data = build(fill)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.read("huge.bin") == payload
        assert archive.testzip() is None


def test_zip64_end_record_for_many_entries():
    total = 70000

    def fill(writer: ZipWriter) -> None:
        for index in range(total):
            writer.add_blob(f"f{index}", b"", 0, 0, STORED)

    data = build(fill)
    assert b"PK\x06\x06" in data[-200:]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
    assert len(names) == total
    assert names[-1] == f"f{total - 1}"


def test_finish_rejects_open_entry():
    writer = ZipWriter(io.BytesIO())
    writer.open_stream("open.bin", STORED, 1)
    with pytest.raises(RuntimeError):
        writer.finish()


def test_double_open_stream_rejected():
    writer = ZipWriter(io.BytesIO())
    writer.open_stream("one.bin", STORED, 1)
    with pytest.raises(RuntimeError):
        writer.open_stream("two.bin", STORED, 1)
