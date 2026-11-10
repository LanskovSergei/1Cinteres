"""Классификация справки по кейсам.

Перенесено из области Диагностика. Порядок проверок важен: сначала то, что
чинится на сервере, затем отсутствие марок, номенклатура, соответствие и
только потом статусы — иначе справка попадёт не в свой кейс.
"""
from __future__ import annotations

from dataclasses import dataclass

MANUAL = -1  # битые ссылки: лечится на сервере с синхронизацией на точку
OK = 0
CASE_NOMENCLATURE = 1
CASE_STATUSES = 2
CASE_LINK = 3
CASE_NO_MARKS = 4


@dataclass
class ReferenceCounters:
    marks_total: int = 0
    in_stock: int = 0
    required: int = 0
    broken_refs: int = 0
    without_alcohol: int = 0
    wrong_nomenclature: int = 0
    without_link: int = 0
    not_in_egais: int = 0
    in_egais_other_status: int = 0
    egais_data: str = "none"  # codes, quantity, none


def classify(c: ReferenceCounters) -> tuple[int, str]:
    if c.broken_refs:
        return MANUAL, (
            f"Марок с битой ссылкой: {c.broken_refs}. "
            "Провести на сервере и синхронизировать на точку"
        )

    if c.marks_total == 0:
        return CASE_NO_MARKS, "По справке нет ни одной марки в 1С"

    if c.without_alcohol or c.wrong_nomenclature:
        return CASE_NOMENCLATURE, (
            f"Пустая алкопродукция: {c.without_alcohol}, "
            f"неверная номенклатура: {c.wrong_nomenclature}"
        )

    if c.without_link:
        return CASE_LINK, f"Нет соответствия номенклатуры для {c.without_link} марок"

    if c.in_stock < c.required or c.not_in_egais or c.in_egais_other_status:
        return CASE_STATUSES, (
            f"В наличии {c.in_stock} из {c.required}. "
            f"Нет на балансе ЕГАИС: {c.not_in_egais}, "
            f"на балансе с другим статусом: {c.in_egais_other_status}"
        )

    if c.egais_data != "codes":
        return OK, "Количество сходится, но кодов марок для сверки нет"

    return OK, ""
