from datetime import datetime

from app.engine.reconcile import reconcile
from app.models import EgaisBalance, Mark, ReconcileRequest

BALANCE_AT = datetime(2026, 10, 1, 12, 0)


def code(n: int) -> str:
    return f"{n:0>70}"


def test_sold_mark_returned_to_stock_when_on_balance():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[Mark(code=code(1), status="Реализована", moved_at=datetime(2026, 9, 1))],
        egais=EgaisBalance(codes=[code(1)], received_at=BALANCE_AT),
    )
    res = reconcile(req)
    assert [(c.old_status, c.new_status) for c in res.status_changes] == [
        ("Реализована", "ВНаличии")
    ]
    assert res.status_changes[0].confirmed_by_egais is True


def test_mark_moved_after_balance_is_not_touched():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[Mark(code=code(1), status="Реализована", moved_at=datetime(2026, 10, 5))],
        egais=EgaisBalance(codes=[code(1)], received_at=BALANCE_AT),
    )
    assert reconcile(req).status_changes == []


def test_mark_not_on_balance_becomes_sold():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[Mark(code=code(1), status="ВНаличии", moved_at=datetime(2026, 9, 1))],
        egais=EgaisBalance(codes=[code(2)], received_at=BALANCE_AT),
    )
    res = reconcile(req)
    assert res.status_changes[0].new_status == "Реализована"
    assert any(i.kind == "marks_missing_in_1c" for i in res.issues)


def test_scanned_marks_are_not_written_off():
    marks = [Mark(code=code(i), status="ВНаличии") for i in range(1, 4)]
    req = ReconcileRequest(
        reference="FB-1",
        marks=marks,
        egais=EgaisBalance(codes=[code(1), code(2), code(3)], received_at=BALANCE_AT),
        scanned_codes=[code(1), code(2)],
        inventory_loaded=True,
        act_quantity=1,
    )
    res = reconcile(req)
    assert res.to_write_off == 1
    assert not [i for i in res.issues if i.kind == "act_quantity_mismatch"]


def test_quantity_only_picks_candidates_by_shortage():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[
            Mark(code=code(1), status="ВНаличии"),
            Mark(code=code(2), status="Реализована", has_receipt=False),
        ],
        egais=EgaisBalance(quantity=2, received_at=BALANCE_AT),
    )
    res = reconcile(req)
    assert res.data_source == "quantity"
    assert len(res.status_changes) == 1
    assert res.status_changes[0].confirmed_by_egais is False
    assert "столько же" in res.status_changes[0].reason


def test_sold_with_receipt_is_not_a_candidate():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[Mark(code=code(2), status="Реализована", has_receipt=True)],
        egais=EgaisBalance(quantity=1, received_at=BALANCE_AT),
    )
    assert reconcile(req).status_changes == []


def test_no_inventory_file_does_not_blame_the_act():
    req = ReconcileRequest(
        reference="FB-1",
        marks=[Mark(code=code(1), status="ВНаличии")],
        egais=EgaisBalance(quantity=11),
        act_quantity=1,
        inventory_loaded=False,
    )
    res = reconcile(req)
    kinds = {i.kind for i in res.issues}
    assert "act_quantity_mismatch" not in kinds
    assert "inventory_not_loaded" in kinds


def test_no_egais_data_gives_case_4_when_no_marks():
    res = reconcile(ReconcileRequest(reference="FB-1"))
    assert res.case == 4
    assert res.issues[0].kind == "no_egais_data"
