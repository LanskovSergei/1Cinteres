"""Контракт с 1С: что обработка присылает и что получает в ответ."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Mark(BaseModel):
    code: str = Field(description="Код марки как он записан в 1С")
    status: str = Field(description="Статус в 1С: ВНаличии, Реализована, ВРезерве")
    moved_at: datetime | None = Field(
        default=None, description="Дата документа-основания: последнее движение марки в 1С"
    )
    has_receipt: bool = Field(
        default=False, description="Есть проведённый чек с этой маркой"
    )


class EgaisBalance(BaseModel):
    """Остатки ЕГАИС по справке.

    Либо коды марок (ответ по регистру №3), либо только количество (регистр №1).
    """

    codes: list[str] | None = None
    quantity: int | None = None
    received_at: datetime | None = None


class ReconcileRequest(BaseModel):
    reference: str = Field(description="Справка 2")
    marks: list[Mark] = Field(default_factory=list)
    egais: EgaisBalance = Field(default_factory=EgaisBalance)
    scanned_codes: list[str] = Field(
        default_factory=list, description="Марки из файла инвентаризации: они в магазине"
    )
    inventory_loaded: bool = Field(
        default=False, description="Файл инвентаризации загружен (иначе вычитать нечего)"
    )
    act_quantity: int | None = Field(
        default=None, description="Количество в строке акта списания"
    )


class StatusChange(BaseModel):
    code: str
    old_status: str
    new_status: str
    reason: str
    confirmed_by_egais: bool = Field(
        description="True — состояние подтверждено ЕГАИС, False — гипотеза по количеству"
    )


class Issue(BaseModel):
    kind: str
    message: str


class ReconcileResponse(BaseModel):
    reference: str
    case: int = Field(description="0 — вопросов нет, 2 — статусы, 4 — марок нет")
    data_source: str = Field(description="codes, quantity или none")
    in_stock_1c: int
    on_balance_egais: int | None
    scanned: int
    to_write_off: int | None
    act_quantity: int | None
    status_changes: list[StatusChange] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    elapsed_ms: float = 0
    marks_processed: int = 0


class InventoryParseRequest(BaseModel):
    content: str = Field(description="Текст файла инвентаризации")


class InventoryParseResponse(BaseModel):
    codes: list[str]
    count: int
    elapsed_ms: float = 0


class NomenclatureCandidate(BaseModel):
    id: str
    name: str
    kind: str | None = None
    volume: float | None = None
    quantity: float | None = None
    already_linked: bool = False
    source: str = ""


class MatchRequest(BaseModel):
    alcohol_name: str
    alcohol_kind: str | None = None
    alcohol_volume: float | None = None
    required_quantity: float | None = None
    candidates: list[NomenclatureCandidate] = Field(default_factory=list)
    check_volume: bool = False


class ScoredCandidate(BaseModel):
    id: str
    name: str
    score: int
    source: str


class MatchResponse(BaseModel):
    best: ScoredCandidate | None = None
    reliable: bool = False
    explanation: str = ""
    candidates: list[ScoredCandidate] = Field(default_factory=list)
    elapsed_ms: float = 0
