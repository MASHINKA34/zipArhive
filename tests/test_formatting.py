from __future__ import annotations

import pytest

from core.formatting import (
    human_duration,
    human_size,
    human_speed,
    natural_key,
    plural_files,
    plural_items,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0 Б"),
        (1, "1 Б"),
        (1023, "1023 Б"),
        (1024, "1 КБ"),
        (1536, "2 КБ"),
        (1024 * 1024, "1 МБ"),
        (int(1.5 * 1024 * 1024), "1,5 МБ"),
        (1024 ** 3, "1 ГБ"),
        (1024 ** 4, "1 ТБ"),
        (1024 ** 5, "1 ПБ"),
        (1024 ** 6, "1024 ПБ"),
        (-5, "0 Б"),
    ],
)
def test_human_size(value, expected):
    assert human_size(value) == expected


@pytest.mark.parametrize(
    "count,expected",
    [
        (0, "файлов"), (1, "файл"), (2, "файла"), (4, "файла"), (5, "файлов"),
        (11, "файлов"), (12, "файлов"), (14, "файлов"), (21, "файл"),
        (22, "файла"), (101, "файл"), (111, "файлов"), (1002, "файла"),
    ],
)
def test_plural_files(count, expected):
    assert plural_files(count) == expected


def test_plural_items():
    assert plural_items(1) == "элемент"
    assert plural_items(3) == "элемента"
    assert plural_items(15) == "элементов"


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "1 с"), (0.4, "1 с"), (12, "12 с"), (59, "59 с"),
        (60, "1 мин 00 с"), (125, "2 мин 05 с"), (3600, "1 ч 00 мин"),
        (7325, "2 ч 02 мин"),
    ],
)
def test_human_duration(seconds, expected):
    assert human_duration(seconds) == expected


def test_human_speed():
    assert human_speed(0) == "—"
    assert human_speed(1024 * 1024) == "1 МБ/с"


def test_natural_key_orders_numbers():
    names = ["file10.txt", "file2.txt", "File1.txt", "alpha.txt"]
    assert sorted(names, key=natural_key) == [
        "alpha.txt", "File1.txt", "file2.txt", "file10.txt",
    ]


def test_natural_key_is_case_insensitive():
    assert natural_key("ABC") == natural_key("abc")
