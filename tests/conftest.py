from __future__ import annotations

import os
import random
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEXT_SAMPLE = b"quick zip payload %d: alpha beta gamma delta epsilon\n"


def write_file(path: str, data: bytes) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def text_blob(size: int, seed: int = 0) -> bytes:
    chunks = []
    total = 0
    counter = seed
    while total < size:
        piece = TEXT_SAMPLE % counter
        chunks.append(piece)
        total += len(piece)
        counter += 1
    return b"".join(chunks)[:size]


def random_blob(size: int, seed: int = 0) -> bytes:
    return random.Random(seed).randbytes(size)


@pytest.fixture
def sample_tree(tmp_path):
    root = tmp_path / "проект"
    write_file(str(root / "readme.md"), text_blob(2048))
    write_file(str(root / "src" / "main.py"), text_blob(9000, 3))
    write_file(str(root / "src" / "utils" / "helpers.py"), text_blob(4500, 9))
    write_file(str(root / "assets" / "logo.png"), random_blob(30000, 11))
    write_file(str(root / "assets" / "видео.mp4"), random_blob(120000, 13))
    write_file(str(root / "пусто.txt"), b"")
    (root / "пустая_папка").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture(scope="session")
def qt_app():
    from PyQt6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application
