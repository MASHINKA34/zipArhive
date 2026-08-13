from __future__ import annotations

import re

_SIZE_UNITS = ("Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ")


def human_size(num_bytes: int) -> str:
    value = float(max(0, num_bytes))
    idx = 0
    limit = len(_SIZE_UNITS) - 1
    while value >= 1024.0 and idx < limit:
        value /= 1024.0
        idx += 1
    unit = _SIZE_UNITS[idx]
    if idx <= 1:
        return f"{round(value)} {unit}"
    rounded = round(value, 1)
    if rounded == int(rounded):
        return f"{int(rounded)} {unit}"
    return f"{rounded:.1f}".replace(".", ",") + f" {unit}"


def human_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec <= 0:
        return "—"
    return f"{human_size(int(bytes_per_sec))}/с"


def plural(n: int, one: str, few: str, many: str) -> str:
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not (12 <= mod100 <= 14):
        return few
    return many


def plural_files(n: int) -> str:
    return plural(n, "файл", "файла", "файлов")


def plural_items(n: int) -> str:
    return plural(n, "элемент", "элемента", "элементов")


def human_duration(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:
        return "—"
    total = int(seconds + 0.5)
    if total < 60:
        return f"{max(total, 1)} с"
    minutes, sec = divmod(total, 60)
    if minutes < 60:
        return f"{minutes} мин {sec:02d} с"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes:02d} мин"


def extension_of(name: str) -> str:
    dot = name.rfind(".")
    if dot <= 0:
        return ""
    return name[dot + 1:].lower()


_DIGITS_RE = re.compile(r"(\d+)")


def natural_key(name: str) -> tuple:
    parts = _DIGITS_RE.split(name.lower())
    return tuple(
        (0, int(part), "") if index & 1 else (1, 0, part)
        for index, part in enumerate(parts)
    )
