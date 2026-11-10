from app.engine.classify import ReferenceCounters, classify


def test_broken_refs_go_to_manual():
    case, text = classify(ReferenceCounters(marks_total=5, broken_refs=1))
    assert case == -1 and "сервере" in text


def test_no_marks_is_case_4():
    assert classify(ReferenceCounters(marks_total=0))[0] == 4


def test_nomenclature_before_statuses():
    c = ReferenceCounters(marks_total=5, in_stock=4, required=5, without_alcohol=1)
    assert classify(c)[0] == 1


def test_statuses_case_even_when_quantity_matches():
    c = ReferenceCounters(
        marks_total=6, in_stock=6, required=6, not_in_egais=2, egais_data="codes"
    )
    assert classify(c)[0] == 2


def test_clean_reference():
    c = ReferenceCounters(marks_total=6, in_stock=6, required=6, egais_data="codes")
    assert classify(c) == (0, "")
