from app.engine import codes

LONG = "A" * 70
OTHER = "B" * 70


def test_normalize_strips_noise():
    assert codes.normalize('  "ABC-123" ') == "ABC123"


def test_parse_inventory_takes_long_tokens_only():
    text = f"шапка;{LONG}\n короткий \t{OTHER}\n{LONG}"
    result = codes.parse_inventory(text)
    assert result == [LONG, OTHER]


def test_parse_inventory_empty():
    assert codes.parse_inventory("") == []


def test_index_normalizes():
    assert codes.index([f" {LONG} "]) == {LONG}
