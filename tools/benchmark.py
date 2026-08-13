from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.formatting import human_size
from core.packer import PackOptions, create_zip, default_workers
from core.scanner import collect_items, scan_tree

WORDS = [
    ("%s_%d" % (stem, index)).encode()
    for index in range(512)
    for stem in ("value", "packer", "config", "handler", "buffer", "session",
                 "index", "result", "stream", "target")
]


def make_text(size: int, seed: int) -> bytes:
    rng = random.Random(seed)
    parts: list[bytes] = []
    total = 0
    while total < size:
        line = b" ".join(rng.choices(WORDS, k=12)) + b"\n"
        parts.append(line)
        total += len(line)
    return b"".join(parts)[:size]


def build_corpus(root: str, profile: str) -> None:
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    rng = random.Random(1234)
    if profile in ("small", "mixed"):
        for group in range(40):
            folder = os.path.join(root, f"src_{group:02d}")
            os.makedirs(folder, exist_ok=True)
            for index in range(125):
                size = rng.randint(2 << 10, 96 << 10)
                path = os.path.join(folder, f"module_{index:03d}.py")
                with open(path, "wb") as handle:
                    handle.write(make_text(size, index))
    if profile in ("media", "mixed"):
        folder = os.path.join(root, "media")
        os.makedirs(folder, exist_ok=True)
        for index in range(12):
            path = os.path.join(folder, f"clip_{index:02d}.mp4")
            with open(path, "wb") as handle:
                handle.write(rng.randbytes(24 << 20))
    if profile in ("large", "mixed"):
        folder = os.path.join(root, "logs")
        os.makedirs(folder, exist_ok=True)
        for index in range(2):
            path = os.path.join(folder, f"server_{index}.log")
            with open(path, "wb") as handle:
                handle.write(make_text(160 << 20, index * 7919))


def baseline_zip(zip_path: str, items) -> int:
    written = 0
    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as archive:
        for item in items:
            if item.is_dir:
                continue
            try:
                archive.write(item.src, item.arcname)
                written += 1
            except (OSError, ValueError):
                pass
    return written


def run(label: str, function, zip_path: str) -> tuple[float, int]:
    if os.path.exists(zip_path):
        os.remove(zip_path)
    started = time.perf_counter()
    function()
    elapsed = time.perf_counter() - started
    size = os.path.getsize(zip_path)
    print(f"  {label:<28} {elapsed:7.2f} с   архив {human_size(size):>10}")
    return elapsed, size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="mixed",
                        choices=["small", "media", "large", "mixed"])
    parser.add_argument("--root", default="")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    base = args.root or os.path.join(
        os.environ.get("TEMP", "."), "quickzip_bench"
    )
    corpus = os.path.join(base, "corpus")
    print(f"Профиль: {args.profile}, каталог: {corpus}")
    if not os.path.isdir(corpus) or not args.keep:
        print("Генерация набора данных…")
        build_corpus(corpus, args.profile)

    started = time.perf_counter()
    root = scan_tree(corpus)
    scan_time = time.perf_counter() - started
    items = collect_items([root])
    total = sum(item.size for item in items)
    print(
        f"Файлов: {root.files}, объём: {human_size(total)}, "
        f"сканирование: {scan_time:.2f} с, потоков: {default_workers()}"
    )

    old_path = os.path.join(base, "baseline.zip")
    new_path = os.path.join(base, "quickzip.zip")

    old_time, old_size = run(
        "zipfile (было)", lambda: baseline_zip(old_path, items), old_path
    )
    results = []
    for label, options in (
        ("QuickZip быстро", PackOptions(level=1)),
        ("QuickZip обычно", PackOptions(level=6)),
        ("QuickZip максимум", PackOptions(level=9, smart_store=False)),
    ):
        results.append(
            (label,) + run(label, lambda o=options: create_zip(
                new_path, items, o), new_path)
        )

    print()
    for label, elapsed, size in results:
        speed = total / elapsed / (1 << 20) if elapsed else 0
        print(
            f"  {label:<28} ускорение x{old_time / elapsed:5.1f}   "
            f"{speed:7.0f} МБ/с   размер {size / old_size * 100:5.1f}% от "
            f"базового"
        )

    if not args.keep:
        for path in (old_path, new_path):
            if os.path.exists(path):
                os.remove(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
