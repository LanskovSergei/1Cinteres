"""Коды акцизных марок: нормализация и разбор файла инвентаризации.

Перенесено из области Кейс5_Инвентаризация модуля обработки 1С.
"""
from __future__ import annotations

import re

# Старые марки (PDF417) — 68 символов, новые (DataMatrix) — около 150.
MIN_CODE_LENGTH = 68

_SEPARATORS = re.compile(r"[\r\n\t;,\"']+")
_NON_CODE = re.compile(r"[^0-9A-Za-z]")


def normalize(code: str) -> str:
    """Приводит код к виду, в котором его можно сравнивать между 1С, ЕГАИС и файлом.

    Пробелы, кавычки и служебные символы убираются, регистр сохраняется:
    в коде марки значимы и буквы, и цифры.
    """
    if not code:
        return ""
    return _NON_CODE.sub("", code.strip())


def looks_like_mark(code: str) -> bool:
    return len(normalize(code)) >= MIN_CODE_LENGTH


def parse_inventory(text: str) -> list[str]:
    """Достаёт коды марок из выгрузки инвентаризации.

    Формат файла заказчика (.1ct) — табличный документ 1С; сюда приходит его
    текстовое представление или выгрузка в CSV. Поэтому разбор устроен терпимо:
    текст режется по разделителям, кодами считаются достаточно длинные фрагменты.
    Дубли убираются, порядок сохраняется.
    """
    seen: set[str] = set()
    result: list[str] = []

    for chunk in _SEPARATORS.split(text or ""):
        code = normalize(chunk)
        if len(code) < MIN_CODE_LENGTH or code in seen:
            continue
        seen.add(code)
        result.append(code)

    return result


def index(codes: list[str]) -> set[str]:
    """Множество нормализованных кодов — для проверки вхождения за константу."""
    return {normalize(c) for c in codes if c}
