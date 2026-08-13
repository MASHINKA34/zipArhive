from __future__ import annotations

import struct
import sys
import time
from dataclasses import dataclass, field
from typing import BinaryIO

STORED = 0
DEFLATED = 8

_SIG_LOCAL = b"PK\x03\x04"
_SIG_CENTRAL = b"PK\x01\x02"
_SIG_END = b"PK\x05\x06"
_SIG_DESCRIPTOR = b"PK\x07\x08"
_SIG_END64 = b"PK\x06\x06"
_SIG_LOCATOR64 = b"PK\x06\x07"

_LOCAL_FMT = "<4s2B4HL2L2H"
_CENTRAL_FMT = "<4s4B4HL2L5H2L"
_END_FMT = "<4s4H2LH"
_END64_FMT = "<4sQ2H2L4Q"
_LOCATOR64_FMT = "<4sLQL"

_MAX32 = 0xFFFFFFFF
_MAX16 = 0xFFFF

_FLAG_DESCRIPTOR = 0x0008
_FLAG_UTF8 = 0x0800

_VERSION_BASE = 20
_VERSION_ZIP64 = 45
_CREATE_SYSTEM = 0 if sys.platform in ("win32", "cygwin") else 3
_CREATE_VERSION = 63

_DOS_EPOCH = (1980, 1, 1, 0, 0, 0)


def dos_timestamp(mtime: float) -> tuple[int, int]:
    try:
        parts = time.localtime(mtime)
        year, month, day = parts.tm_year, parts.tm_mon, parts.tm_mday
        hour, minute, second = parts.tm_hour, parts.tm_min, parts.tm_sec
    except (OSError, OverflowError, ValueError):
        year, month, day, hour, minute, second = _DOS_EPOCH
    if year < 1980:
        year, month, day, hour, minute, second = _DOS_EPOCH
    elif year > 2107:
        year, month, day, hour, minute, second = 2107, 12, 31, 23, 59, 58
    dos_date = ((year - 1980) << 9) | (month << 5) | day
    dos_time = (hour << 11) | (minute << 5) | (second // 2)
    return dos_time, dos_date


def encode_name(name: str, is_dir: bool) -> tuple[bytes, int]:
    normalized = name.replace("\\", "/").lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    if is_dir and not normalized.endswith("/"):
        normalized += "/"
    try:
        return normalized.encode("ascii"), 0
    except UnicodeEncodeError:
        return normalized.encode("utf-8"), _FLAG_UTF8


@dataclass(slots=True)
class ZipEntry:
    name: bytes
    flags: int
    method: int
    dos_time: int
    dos_date: int
    external_attr: int
    offset: int = 0
    crc: int = 0
    compressed_size: int = 0
    size: int = 0
    zip64: bool = False


@dataclass(slots=True)
class ZipWriter:
    stream: BinaryIO
    offset: int = 0
    entries: list[ZipEntry] = field(default_factory=list)
    _open_entry: ZipEntry | None = None

    def _write(self, data: bytes) -> None:
        self.stream.write(data)
        self.offset += len(data)

    def add_directory(self, arcname: str, mtime: float = 0.0) -> None:
        name, utf8 = encode_name(arcname, True)
        dos_time, dos_date = dos_timestamp(mtime or time.time())
        entry = ZipEntry(
            name=name,
            flags=utf8,
            method=STORED,
            dos_time=dos_time,
            dos_date=dos_date,
            external_attr=0x10 | (0o40755 << 16),
            offset=self.offset,
        )
        self._write(_local_header(entry))
        self.entries.append(entry)

    def add_blob(
        self,
        arcname: str,
        data: bytes,
        crc: int,
        size: int,
        method: int,
        mtime: float = 0.0,
        mode: int = 0o600,
    ) -> None:
        name, utf8 = encode_name(arcname, False)
        dos_time, dos_date = dos_timestamp(mtime or time.time())
        entry = ZipEntry(
            name=name,
            flags=utf8,
            method=method,
            dos_time=dos_time,
            dos_date=dos_date,
            external_attr=((mode & 0xFFFF) << 16) | 0x20,
            offset=self.offset,
            crc=crc,
            compressed_size=len(data),
            size=size,
            zip64=size > _MAX32 or len(data) > _MAX32,
        )
        self._write(_local_header(entry))
        self._write(data)
        self.entries.append(entry)

    def open_stream(
        self,
        arcname: str,
        method: int,
        expected_size: int,
        mtime: float = 0.0,
        mode: int = 0o600,
    ) -> ZipEntry:
        if self._open_entry is not None:
            raise RuntimeError("previous entry is still open")
        name, utf8 = encode_name(arcname, False)
        dos_time, dos_date = dos_timestamp(mtime or time.time())
        entry = ZipEntry(
            name=name,
            flags=utf8 | _FLAG_DESCRIPTOR,
            method=method,
            dos_time=dos_time,
            dos_date=dos_date,
            external_attr=((mode & 0xFFFF) << 16) | 0x20,
            offset=self.offset,
            zip64=expected_size > _MAX32 - (1 << 26),
        )
        self._write(_local_header(entry))
        self._open_entry = entry
        return entry

    def write_stream(self, data: bytes) -> None:
        if self._open_entry is None:
            raise RuntimeError("no open entry")
        self._write(data)

    def close_stream(self, crc: int, compressed_size: int, size: int) -> None:
        entry = self._open_entry
        if entry is None:
            raise RuntimeError("no open entry")
        entry.crc = crc & _MAX32
        entry.compressed_size = compressed_size
        entry.size = size
        if entry.zip64:
            self._write(
                struct.pack(
                    "<4sLQQ", _SIG_DESCRIPTOR, entry.crc,
                    compressed_size, size,
                )
            )
        else:
            self._write(
                struct.pack(
                    "<4s3L", _SIG_DESCRIPTOR, entry.crc,
                    compressed_size & _MAX32, size & _MAX32,
                )
            )
        self.entries.append(entry)
        self._open_entry = None

    def finish(self) -> int:
        if self._open_entry is not None:
            raise RuntimeError("entry is still open")
        directory_offset = self.offset
        for entry in self.entries:
            self._write(_central_record(entry))
        directory_size = self.offset - directory_offset
        count = len(self.entries)
        needs64 = (
            count > _MAX16
            or directory_size > _MAX32
            or directory_offset > _MAX32
        )
        if needs64:
            end64_offset = self.offset
            self._write(
                struct.pack(
                    _END64_FMT, _SIG_END64, 44, _CREATE_VERSION,
                    _VERSION_ZIP64, 0, 0, count, count,
                    directory_size, directory_offset,
                )
            )
            self._write(
                struct.pack(_LOCATOR64_FMT, _SIG_LOCATOR64, 0, end64_offset, 1)
            )
        self._write(
            struct.pack(
                _END_FMT, _SIG_END, 0, 0,
                min(count, _MAX16), min(count, _MAX16),
                min(directory_size, _MAX32), min(directory_offset, _MAX32), 0,
            )
        )
        return self.offset


def _local_header(entry: ZipEntry) -> bytes:
    if entry.flags & _FLAG_DESCRIPTOR:
        crc = size = compressed = 0
    else:
        crc = entry.crc
        size = entry.size
        compressed = entry.compressed_size
    if entry.zip64:
        extra = struct.pack("<HHQQ", 0x0001, 16, size, compressed)
        size_field = compressed_field = _MAX32
        version = _VERSION_ZIP64
    else:
        extra = b""
        size_field = size
        compressed_field = compressed
        version = _VERSION_BASE
    return struct.pack(
        _LOCAL_FMT, _SIG_LOCAL, version, 0, entry.flags, entry.method,
        entry.dos_time, entry.dos_date, crc, compressed_field, size_field,
        len(entry.name), len(extra),
    ) + entry.name + extra


def _central_record(entry: ZipEntry) -> bytes:
    extra_values: list[int] = []
    size_field = entry.size
    compressed_field = entry.compressed_size
    offset_field = entry.offset
    if entry.size > _MAX32:
        extra_values.append(entry.size)
        size_field = _MAX32
    if entry.compressed_size > _MAX32:
        extra_values.append(entry.compressed_size)
        compressed_field = _MAX32
    if entry.offset > _MAX32:
        extra_values.append(entry.offset)
        offset_field = _MAX32
    if extra_values:
        extra = struct.pack(
            f"<HH{len(extra_values)}Q", 0x0001, 8 * len(extra_values),
            *extra_values,
        )
        version = _VERSION_ZIP64
    else:
        extra = b""
        version = _VERSION_ZIP64 if entry.zip64 else _VERSION_BASE
    return struct.pack(
        _CENTRAL_FMT, _SIG_CENTRAL, _CREATE_VERSION, _CREATE_SYSTEM,
        version, 0, entry.flags, entry.method, entry.dos_time, entry.dos_date,
        entry.crc, compressed_field, size_field, len(entry.name), len(extra),
        0, 0, 0, entry.external_attr, offset_field,
    ) + entry.name + extra
