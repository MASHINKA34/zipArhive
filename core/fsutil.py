from __future__ import annotations

import os
import sys

_LONG_PREFIX = "\\\\?\\"
_LONG_THRESHOLD = 240
_IS_WINDOWS = sys.platform == "win32"


def long_path(path: str) -> str:
    if not _IS_WINDOWS or len(path) < _LONG_THRESHOLD:
        return path
    if path.startswith(_LONG_PREFIX):
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\"):
        return _LONG_PREFIX + "UNC" + absolute[1:]
    return _LONG_PREFIX + absolute
