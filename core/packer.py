from __future__ import annotations

import logging
import os
import threading
import time
import zlib
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Iterable, Iterator, Sequence

from core.formatting import extension_of
from core.fsutil import long_path
from core.zipwriter import DEFLATED, STORED, ZipWriter

STORE_EXTENSIONS = frozenset({
    "7z", "aac", "apk", "appx", "avi", "avif", "br", "bz2", "cab", "crx",
    "docm", "docx", "dmg", "epub", "flac", "flv", "gif", "gz", "heic",
    "heif", "ipa", "jar", "jpeg", "jpg", "jxl", "lz4", "lzma", "m4a",
    "m4v", "mkv", "mov", "mp3", "mp4", "mpg", "mpeg", "odp", "ods", "odt",
    "oga", "ogg", "ogv", "opus", "pptm", "pptx", "png", "rar", "tgz",
    "vsdx", "war", "webm", "webp", "whl", "wma", "wmv", "xlsm", "xlsx",
    "xz", "zip", "zst", "zstd",
})

PROBE_SIZE = 1 << 17
PROBE_RATIO = 0.94

_DEFLATE_EOS = b"\x01\x00\x00\xff\xff"

_CRC_POLY = 0xEDB88320
_CRC_ONE = 0x80000000

log = logging.getLogger("quickzip.packer")


@dataclass(slots=True)
class ArchiveItem:
    src: str
    arcname: str
    size: int = 0
    mtime: float = 0.0
    is_dir: bool = False


@dataclass(slots=True)
class PackOptions:
    level: int = 6
    smart_store: bool = True
    workers: int = 0
    chunk_size: int = 4 << 20
    inline_limit: int = 8 << 20
    batch_bytes: int = 1 << 20
    batch_count: int = 64
    batch_item_limit: int = 1 << 18
    memory_budget: int = 192 << 20
    write_buffer: int = 4 << 20
    progress_interval: float = 0.05


@dataclass(slots=True)
class PackResult:
    written: int = 0
    skipped: int = 0
    total_size: int = 0
    archive_size: int = 0
    elapsed: float = 0.0
    cancelled: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        if self.total_size <= 0:
            return 1.0
        return self.archive_size / self.total_size


def default_workers() -> int:
    return max(2, min(16, os.cpu_count() or 4))


def _multmodp(a: int, b: int) -> int:
    mask = _CRC_ONE
    product = 0
    while True:
        if a & mask:
            product ^= b
            if not a & (mask - 1):
                return product
        mask >>= 1
        b = (b >> 1) ^ _CRC_POLY if b & 1 else b >> 1


def _x2n_table() -> tuple[int, ...]:
    table = [1 << 30]
    for _ in range(31):
        table.append(_multmodp(table[-1], table[-1]))
    return tuple(table)


_X2N = _x2n_table()


@lru_cache(maxsize=64)
def _shift_operator(length: int) -> int:
    operator = _CRC_ONE
    power = 3
    while length:
        if length & 1:
            operator = _multmodp(_X2N[power & 31], operator)
        length >>= 1
        power += 1
    return operator


def crc32_combine(crc1: int, crc2: int, len2: int) -> int:
    if len2 <= 0:
        return crc1 & 0xFFFFFFFF
    combined = _multmodp(_shift_operator(len2), crc1 & 0xFFFFFFFF)
    return (combined ^ (crc2 & 0xFFFFFFFF)) & 0xFFFFFFFF


def _deflate(data: bytes, level: int) -> bytes:
    compressor = zlib.compressobj(level, zlib.DEFLATED, -15)
    return compressor.compress(data) + compressor.flush()


def _deflate_part(data: bytes, level: int, last: bool) -> bytes:
    compressor = zlib.compressobj(level, zlib.DEFLATED, -15)
    mode = zlib.Z_FINISH if last else zlib.Z_FULL_FLUSH
    return compressor.compress(data) + compressor.flush(mode)


@dataclass(slots=True)
class _Blob:
    item: ArchiveItem
    payload: bytes
    crc: int
    size: int
    method: int
    error: str = ""


@dataclass(slots=True)
class _Part:
    payload: bytes
    crc: int
    size: int
    error: str = ""


@dataclass(slots=True)
class _Chunk:
    item: ArchiveItem
    offset: int
    length: int
    last: bool
    method: int


@dataclass(slots=True)
class _Unit:
    kind: str
    payload: object
    charge: int


def _read_batch(
    items: Sequence[ArchiveItem], level: int, smart_store: bool
) -> list[_Blob]:
    out: list[_Blob] = []
    for item in items:
        try:
            with open(long_path(item.src), "rb", buffering=0) as handle:
                data = handle.read()
        except OSError as exc:
            out.append(_Blob(item, b"", 0, 0, STORED, str(exc)))
            continue
        crc = zlib.crc32(data)
        method = STORED
        payload = data
        store = smart_store and extension_of(item.arcname) in STORE_EXTENSIONS
        if not store and data:
            packed = _deflate(data, level)
            if len(packed) < len(data):
                payload = packed
                method = DEFLATED
        out.append(_Blob(item, payload, crc, len(data), method))
    return out


def _read_chunk(chunk: _Chunk, level: int) -> _Part:
    try:
        with open(long_path(chunk.item.src), "rb", buffering=0) as handle:
            handle.seek(chunk.offset)
            data = handle.read(chunk.length)
    except OSError as exc:
        return _Part(b"", 0, 0, str(exc))
    crc = zlib.crc32(data)
    if chunk.method == STORED:
        return _Part(data, crc, len(data))
    return _Part(_deflate_part(data, level, chunk.last), crc, len(data))


def _probe_compressible(path: str, level: int) -> bool:
    try:
        with open(long_path(path), "rb", buffering=0) as handle:
            head = handle.read(PROBE_SIZE)
    except OSError as exc:
        log.warning("Cannot probe %s, will try to compress: %s", path, exc)
        return True
    if len(head) < 4096:
        return True
    compressible = (
        len(_deflate(head, min(level, 1))) < len(head) * PROBE_RATIO
    )
    log.debug("Probe %s: compressible=%s", path, compressible)
    return compressible


def _unique_arcname(arcname: str, used: set[str]) -> str:
    key = arcname.lower()
    if key not in used:
        used.add(key)
        return arcname
    stem, dot, ext = arcname.rpartition(".")
    if not dot or "/" in ext:
        stem, ext = arcname, ""
    else:
        ext = "." + ext
    counter = 1
    while True:
        candidate = f"{stem} ({counter}){ext}"
        if candidate.lower() not in used:
            used.add(candidate.lower())
            return candidate
        counter += 1


def _iter_units(
    items: Sequence[ArchiveItem], options: PackOptions
) -> Iterator[_Unit]:
    batch: list[ArchiveItem] = []
    batch_bytes = 0
    for item in items:
        if item.is_dir:
            if batch:
                yield _Unit("batch", batch, batch_bytes)
                batch, batch_bytes = [], 0
            yield _Unit("dir", item, 0)
            continue
        if item.size <= options.inline_limit:
            if item.size <= options.batch_item_limit:
                batch.append(item)
                batch_bytes += item.size
                if (
                    len(batch) >= options.batch_count
                    or batch_bytes >= options.batch_bytes
                ):
                    yield _Unit("batch", batch, batch_bytes)
                    batch, batch_bytes = [], 0
            else:
                if batch:
                    yield _Unit("batch", batch, batch_bytes)
                    batch, batch_bytes = [], 0
                yield _Unit("batch", [item], item.size)
            continue
        if batch:
            yield _Unit("batch", batch, batch_bytes)
            batch, batch_bytes = [], 0
        store = (
            options.smart_store
            and extension_of(item.arcname) in STORE_EXTENSIONS
        )
        if not store and options.smart_store:
            store = not _probe_compressible(item.src, options.level)
        method = STORED if store else DEFLATED
        log.debug(
            "Streaming large file %s: %d bytes in %d chunks, method=%s",
            item.src, item.size, -(-item.size // options.chunk_size),
            "stored" if store else "deflated",
        )
        offset = 0
        while offset < item.size:
            length = min(options.chunk_size, item.size - offset)
            last = offset + length >= item.size
            yield _Unit(
                "chunk", _Chunk(item, offset, length, last, method), length
            )
            offset += length
    if batch:
        yield _Unit("batch", batch, batch_bytes)


class _Reporter:
    __slots__ = ("_callback", "_total", "_interval", "_last", "_done")

    def __init__(
        self,
        callback: Callable[[int, int, str], None] | None,
        total: int,
        interval: float,
    ) -> None:
        self._callback = callback
        self._total = total
        self._interval = interval
        self._last = 0.0
        self._done = 0

    def advance(self, amount: int, name: str, force: bool = False) -> None:
        self._done += amount
        if self._callback is None:
            return
        now = time.monotonic()
        if force or now - self._last >= self._interval:
            self._last = now
            self._callback(min(self._done, self._total), self._total, name)


def create_zip(
    zip_path: str,
    items: Iterable[ArchiveItem],
    options: PackOptions | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> PackResult:
    opts = options or PackOptions()
    ordered = list(items)
    total_bytes = sum(item.size for item in ordered if not item.is_dir)
    dirs = sum(1 for item in ordered if item.is_dir)
    result = PackResult(total_size=total_bytes)
    reporter = _Reporter(progress, max(total_bytes, 1), opts.progress_interval)
    started = time.monotonic()
    workers = opts.workers or default_workers()
    stop = threading.Event()
    used: set[str] = set()
    states: dict[int, _StreamState] = {}

    def cancelled() -> bool:
        return stop.is_set() or bool(should_cancel and should_cancel())

    log.info(
        "Packing %d items (%d files, %d dirs, %d bytes) -> %s; level=%d "
        "workers=%d smart_store=%s",
        len(ordered), len(ordered) - dirs, dirs, total_bytes, zip_path,
        opts.level, workers, opts.smart_store,
    )
    completed = False
    handle = open(long_path(zip_path), "wb", buffering=opts.write_buffer)
    try:
        writer = ZipWriter(handle)
        pool = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="quickzip"
        )
        try:
            units = _iter_units(ordered, opts)
            pending: deque[tuple[_Unit, Future | None]] = deque()
            inflight = 0
            max_units = workers * 4
            exhausted = False
            while True:
                while (
                    not exhausted
                    and len(pending) < max_units
                    and inflight < opts.memory_budget
                ):
                    if cancelled():
                        exhausted = True
                        break
                    unit = next(units, None)
                    if unit is None:
                        exhausted = True
                        break
                    if unit.kind == "batch":
                        future = pool.submit(
                            _read_batch, unit.payload, opts.level,
                            opts.smart_store,
                        )
                    elif unit.kind == "chunk":
                        future = pool.submit(_read_chunk, unit.payload,
                                             opts.level)
                    else:
                        future = None
                    pending.append((unit, future))
                    inflight += unit.charge
                if not pending:
                    break
                if cancelled():
                    stop.set()
                    for _unit, future in pending:
                        if future is not None:
                            future.cancel()
                    break
                unit, future = pending.popleft()
                inflight -= unit.charge
                if unit.kind == "dir":
                    item = unit.payload
                    writer.add_directory(
                        _unique_arcname(item.arcname, used), item.mtime
                    )
                    result.written += 1
                elif unit.kind == "batch":
                    _write_blobs(writer, future.result(), used, result,
                                 reporter)
                else:
                    _write_chunk(writer, unit.payload, future.result(),
                                 states, used, result, reporter)
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        if cancelled():
            result.cancelled = True
        else:
            result.archive_size = writer.finish()
            completed = True
    finally:
        handle.close()
        if not completed:
            _remove_quietly(zip_path)
    result.elapsed = time.monotonic() - started
    if result.cancelled:
        log.info(
            "Packing cancelled after %.1f s: written=%d skipped=%d",
            result.elapsed, result.written, result.skipped,
        )
    else:
        log.info(
            "Archive written: %s; entries=%d skipped=%d %d -> %d bytes "
            "(%.0f%%) in %.1f s (%.1f MB/s)",
            zip_path, result.written, result.skipped, total_bytes,
            result.archive_size, result.ratio * 100, result.elapsed,
            total_bytes / max(result.elapsed, 0.001) / (1 << 20),
        )
    if progress and not result.cancelled:
        progress(max(total_bytes, 1), max(total_bytes, 1), "")
    return result


@dataclass(slots=True)
class _StreamState:
    opened: bool = False
    crc: int = 0
    size: int = 0
    compressed: int = 0
    broken: bool = False


def _write_blobs(
    writer: ZipWriter,
    blobs: list[_Blob],
    used: set[str],
    result: PackResult,
    reporter: _Reporter,
) -> None:
    debug = log.isEnabledFor(logging.DEBUG)
    for blob in blobs:
        name = os.path.basename(blob.item.src)
        if blob.error:
            result.skipped += 1
            result.warnings.append(f"{name}: {blob.error}")
            log.warning("Skipped unreadable file %s: %s", blob.item.src,
                        blob.error)
            reporter.advance(blob.item.size, name)
            continue
        if debug:
            log.debug("Added %s: %d -> %d bytes (%s)", blob.item.arcname,
                      blob.size, len(blob.payload),
                      "deflated" if blob.method == DEFLATED else "stored")
        writer.add_blob(
            _unique_arcname(blob.item.arcname, used),
            blob.payload,
            blob.crc,
            blob.size,
            blob.method,
            blob.item.mtime,
        )
        result.written += 1
        reporter.advance(blob.size, name)


def _write_chunk(
    writer: ZipWriter,
    chunk: _Chunk,
    part: _Part,
    states: dict[int, _StreamState],
    used: set[str],
    result: PackResult,
    reporter: _Reporter,
) -> None:
    key = id(chunk.item)
    state = states.get(key)
    if state is None:
        state = _StreamState()
        states[key] = state
    name = os.path.basename(chunk.item.src)

    if part.error and not state.broken:
        state.broken = True
        result.warnings.append(f"{name}: {part.error}")
        log.warning(
            "Read failed for %s at offset %d: %s; entry truncated",
            chunk.item.src, chunk.offset, part.error,
        )

    if not state.broken:
        if state.opened:
            state.crc = crc32_combine(state.crc, part.crc, part.size)
        else:
            writer.open_stream(
                _unique_arcname(chunk.item.arcname, used),
                chunk.method,
                chunk.item.size,
                chunk.item.mtime,
            )
            state.opened = True
            state.crc = part.crc
        writer.write_stream(part.payload)
        state.compressed += len(part.payload)
        state.size += part.size

    if chunk.last:
        states.pop(key, None)
        if state.opened:
            if state.broken and chunk.method == DEFLATED:
                writer.write_stream(_DEFLATE_EOS)
                state.compressed += len(_DEFLATE_EOS)
            writer.close_stream(state.crc, state.compressed, state.size)
            result.written += 1
        else:
            result.skipped += 1
    reporter.advance(chunk.length, name)


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        log.debug("Incomplete archive already gone: %s", path)
    except OSError as exc:
        log.warning("Cannot remove incomplete archive %s: %s", path, exc)
    else:
        log.info("Removed incomplete archive %s", path)
