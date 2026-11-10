from app.engine.matching import similarity
from app.engine.matching import match
from app.models import MatchRequest, NomenclatureCandidate


def test_similarity_counts_common_words():
    assert similarity("Водка ГОРНОЕ ОЗЕРО 0,5л", "Водка ГОРНОЕ ОЗЕРО") == 1.0
    assert similarity("Водка", "Вино") == 0.0


def test_linked_candidate_wins_and_is_reliable():
    req = MatchRequest(
        alcohol_name="Водка ГОРНОЕ ОЗЕРО",
        candidates=[
            NomenclatureCandidate(id="1", name="Водка ГОРНОЕ ОЗЕРО 0,5л", already_linked=True, source="марки"),
            NomenclatureCandidate(id="2", name="Вино Кагор", source="поиск"),
        ],
    )
    res = match(req)
    assert res.best.id == "1" and res.reliable is True


def test_wrong_kind_is_filtered_out():
    req = MatchRequest(
        alcohol_name="Водка",
        alcohol_kind="водка",
        candidates=[NomenclatureCandidate(id="1", name="Вино", kind="вино")],
    )
    res = match(req)
    assert res.best is None and "не найдено" in res.explanation


def test_two_equal_candidates_are_not_reliable():
    req = MatchRequest(
        alcohol_name="Водка ГОРНОЕ ОЗЕРО",
        candidates=[
            NomenclatureCandidate(id="1", name="Водка ГОРНОЕ ОЗЕРО", already_linked=True),
            NomenclatureCandidate(id="2", name="Водка ГОРНОЕ ОЗЕРО", already_linked=True),
        ],
    )
    assert match(req).reliable is False
