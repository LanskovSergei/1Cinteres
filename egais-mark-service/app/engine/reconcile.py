"""Сверка марок по одной справке.

Перенесено из областей Кейс2_Сверка и Кейс2_План. Логика та же, что в 1С:
сравниваются три множества — марки в 1С, марки на балансе ЕГАИС и марки,
отсканированные при инвентаризации. Сервис только считает и объясняет,
записывает изменения по-прежнему 1С.
"""
from __future__ import annotations

from app.engine import codes as codes_mod
from app.engine import statuses as st
from app.models import (
    EgaisBalance,
    Issue,
    Mark,
    ReconcileRequest,
    ReconcileResponse,
    StatusChange,
)

SOURCE_CODES = "codes"
SOURCE_QUANTITY = "quantity"
SOURCE_NONE = "none"


def _source(egais: EgaisBalance) -> str:
    if egais.codes:
        return SOURCE_CODES
    if egais.quantity is not None:
        return SOURCE_QUANTITY
    return SOURCE_NONE


def _by_codes(req: ReconcileRequest, scanned: set[str]) -> ReconcileResponse:
    on_balance = codes_mod.index(req.egais.codes or [])
    changes: list[StatusChange] = []
    issues: list[Issue] = []
    to_write_off = 0
    in_stock = 0
    seen: set[str] = set()

    for mark in req.marks:
        code = codes_mod.normalize(mark.code)
        seen.add(code)
        if mark.status == st.IN_STOCK:
            in_stock += 1

        state = st.ON_BALANCE if code in on_balance else st.OFF_BALANCE
        if state == st.ON_BALANCE and code not in scanned:
            to_write_off += 1

        if st.moved_after_balance(mark.moved_at, req.egais.received_at):
            # 1С свежее остатков: марку продали или списали уже после выгрузки.
            continue

        new_status = st.target_status(state, mark.status)
        if new_status:
            changes.append(
                StatusChange(
                    code=code,
                    old_status=mark.status,
                    new_status=new_status,
                    reason=f"ЕГАИС: {st.egais_title(state)}",
                    confirmed_by_egais=True,
                )
            )

    missing = sorted(on_balance - seen)
    if missing:
        to_write_off += sum(1 for code in missing if code not in scanned)
        issues.append(
            Issue(
                kind="marks_missing_in_1c",
                message=(
                    f"На балансе ЕГАИС есть {len(missing)} марок, которых нет в 1С — "
                    "запросите марки по справке 2"
                ),
            )
        )

    return ReconcileResponse(
        reference=req.reference,
        case=2 if (changes or missing) else 0,
        data_source=SOURCE_CODES,
        in_stock_1c=in_stock,
        on_balance_egais=len(on_balance),
        scanned=sum(1 for m in req.marks if codes_mod.normalize(m.code) in scanned),
        to_write_off=to_write_off,
        act_quantity=req.act_quantity,
        status_changes=changes,
        issues=issues,
        marks_processed=len(req.marks),
    )


def _by_quantity(req: ReconcileRequest, scanned: set[str]) -> ReconcileResponse:
    """Кодов марок нет, есть только количество по справке.

    Сверить статусы не с чем, но недостачу видно. Кандидаты на разницу —
    «в резерве» и «реализована» без проведённого чека, не двигавшиеся после
    даты остатков. Если их ровно столько, сколько не хватает, это почти
    наверняка они, но подтверждения ЕГАИС нет, поэтому меняем только после
    проверки человеком.
    """
    on_balance = req.egais.quantity or 0
    in_stock = sum(1 for m in req.marks if m.status == st.IN_STOCK)
    scanned_count = sum(1 for m in req.marks if codes_mod.normalize(m.code) in scanned)

    candidates: list[Mark] = [
        m
        for m in req.marks
        if (m.status == st.RESERVED or (m.status == st.SOLD and not m.has_receipt))
        and not st.moved_after_balance(m.moved_at, req.egais.received_at)
    ]

    shortage = on_balance - in_stock
    changes: list[StatusChange] = []
    issues: list[Issue] = [
        Issue(
            kind="no_mark_codes",
            message=(
                "В остатках только количество, кодов марок нет — "
                "запросите марки по справке 2, иначе статусы сверить не с чем"
            ),
        )
    ]

    if shortage > 0 and candidates:
        exact = len(candidates) == shortage
        reason = (
            f"Не хватает {shortage} марок, и столько же подходящих — проверьте на check1"
            if exact
            else f"Не хватает {shortage}, подходящих кандидатов {len(candidates)} — проверьте вручную"
        )
        for mark in candidates:
            changes.append(
                StatusChange(
                    code=codes_mod.normalize(mark.code),
                    old_status=mark.status,
                    new_status=st.IN_STOCK,
                    reason=reason,
                    confirmed_by_egais=False,
                )
            )

    to_write_off = max(on_balance - scanned_count, 0) if req.inventory_loaded else None

    return ReconcileResponse(
        reference=req.reference,
        case=2,
        data_source=SOURCE_QUANTITY,
        in_stock_1c=in_stock,
        on_balance_egais=on_balance,
        scanned=scanned_count,
        to_write_off=to_write_off,
        act_quantity=req.act_quantity,
        status_changes=changes,
        issues=issues,
        marks_processed=len(req.marks),
    )


def _check_act_quantity(result: ReconcileResponse, inventory_loaded: bool) -> None:
    """Количество в акте должно совпасть с «к списанию»."""
    if result.act_quantity is None or result.to_write_off is None:
        if result.act_quantity is not None and not inventory_loaded:
            result.issues.append(
                Issue(
                    kind="inventory_not_loaded",
                    message=(
                        "Файл инвентаризации не загружен — сколько марок осталось "
                        "в магазине, неизвестно, количество в акте не проверено"
                    ),
                )
            )
        return

    if result.to_write_off != result.act_quantity:
        result.issues.append(
            Issue(
                kind="act_quantity_mismatch",
                message=(
                    f"В акте {result.act_quantity}, по ЕГАИС к списанию {result.to_write_off} "
                    f"(на балансе {result.on_balance_egais}, отсканировано {result.scanned}) — "
                    "поправьте строку акта до отправки"
                ),
            )
        )


def reconcile(req: ReconcileRequest) -> ReconcileResponse:
    scanned = codes_mod.index(req.scanned_codes) if req.inventory_loaded else set()
    source = _source(req.egais)

    if source == SOURCE_CODES:
        result = _by_codes(req, scanned)
    elif source == SOURCE_QUANTITY:
        result = _by_quantity(req, scanned)
    else:
        result = ReconcileResponse(
            reference=req.reference,
            case=4 if not req.marks else 0,
            data_source=SOURCE_NONE,
            in_stock_1c=sum(1 for m in req.marks if m.status == st.IN_STOCK),
            on_balance_egais=None,
            scanned=0,
            to_write_off=None,
            act_quantity=req.act_quantity,
            issues=[
                Issue(
                    kind="no_egais_data",
                    message="Нет полученных остатков ЕГАИС — запросите остатки и повторите",
                )
            ],
            marks_processed=len(req.marks),
        )

    _check_act_quantity(result, req.inventory_loaded)
    return result
