from datetime import datetime

from app.engine import statuses as st


def test_matrix_rules():
    assert st.target_status(st.ON_BALANCE, st.SOLD) == st.IN_STOCK
    assert st.target_status(st.OFF_BALANCE, st.IN_STOCK) == st.SOLD
    assert st.target_status(st.ON_BALANCE, st.IN_STOCK) is None


def test_moved_after_balance():
    balance = datetime(2026, 10, 1, 12, 0)
    assert st.moved_after_balance(datetime(2026, 10, 2), balance) is True
    assert st.moved_after_balance(datetime(2026, 9, 30), balance) is False
    assert st.moved_after_balance(None, balance) is False
