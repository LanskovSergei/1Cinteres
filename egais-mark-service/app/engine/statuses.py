"""Правила статусов марок.

Перенесено из области Кейс2_СтатусыМарок. По ответам заказчика в ЕГАИС два
состояния: «В обороте» и «В архиве». В 1С им соответствуют «В наличии»
и «Реализована»; «В резерве» всегда приводится к состоянию ЕГАИС.
"""
from __future__ import annotations

from datetime import datetime

IN_STOCK = "ВНаличии"
SOLD = "Реализована"
RESERVED = "ВРезерве"
NOT_IN_1C = "НетВ1С"

ON_BALANCE = "НаБалансе"
OFF_BALANCE = "НеНаБалансе"

EGAIS_TITLES = {ON_BALANCE: "В обороте", OFF_BALANCE: "В архиве"}

# (состояние в ЕГАИС, статус в 1С) -> какой статус поставить
MATRIX: dict[tuple[str, str], str] = {
    (ON_BALANCE, SOLD): IN_STOCK,
    (ON_BALANCE, RESERVED): IN_STOCK,
    (OFF_BALANCE, IN_STOCK): SOLD,
    (OFF_BALANCE, RESERVED): SOLD,
}


def egais_title(state: str) -> str:
    return EGAIS_TITLES.get(state, state)


def target_status(egais_state: str, status_1c: str) -> str | None:
    """Новый статус или None, если менять нечего."""
    return MATRIX.get((egais_state, status_1c))


def moved_after_balance(moved_at: datetime | None, balance_at: datetime | None) -> bool:
    """Марка двигалась в 1С после того, как получены остатки.

    Тогда 1С свежее ЕГАИС: марку продали, списали или она пришла по накладной
    уже после выгрузки остатков, и статус трогать нельзя.
    """
    if moved_at is None or balance_at is None:
        return False
    return moved_at > balance_at
