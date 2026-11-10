"""Подбор номенклатуры по алкогольной продукции.

Перенесено из областей Кейс1_ОснованиеТТН и Кейс3_СоответствиеНоменклатуры:
оценка кандидатов в баллах и похожесть наименований по значимым словам.
"""
from __future__ import annotations

import re

from app.models import MatchRequest, MatchResponse, NomenclatureCandidate, ScoredCandidate

_SPLIT = re.compile(r"[\s\"«»'.,;:()\-/\\]+")
MIN_WORD = 3

SCORE_LINKED = 100
SCORE_QUANTITY = 30
SCORE_NAME = 30
RELIABLE_SCORE = 60
RELIABLE_GAP = 20


def significant_words(text: str) -> list[str]:
    words: list[str] = []
    for word in _SPLIT.split((text or "").lower()):
        if len(word) >= MIN_WORD and word not in words:
            words.append(word)
    return words


def similarity(first: str, second: str) -> float:
    """Доля общих значимых слов, 0…1."""
    a, b = significant_words(first), significant_words(second)
    if not a or not b:
        return 0.0
    common = sum(1 for word in a if word in b)
    return common / max(len(a), len(b))


def score(candidate: NomenclatureCandidate, req: MatchRequest) -> int:
    """Отрицательный балл — кандидат не подходит по виду или объёму."""
    if candidate.kind and req.alcohol_kind and candidate.kind != req.alcohol_kind:
        return -1
    if req.check_volume and candidate.volume and candidate.volume != req.alcohol_volume:
        return -1

    value = 0
    if candidate.already_linked:
        value += SCORE_LINKED
    if (
        candidate.quantity is not None
        and req.required_quantity is not None
        and candidate.quantity == req.required_quantity
    ):
        value += SCORE_QUANTITY
    value += round(SCORE_NAME * similarity(candidate.name, req.alcohol_name))
    return value


def match(req: MatchRequest) -> MatchResponse:
    scored = [
        ScoredCandidate(id=c.id, name=c.name, score=s, source=c.source)
        for c in req.candidates
        if (s := score(c, req)) >= 0
    ]
    scored.sort(key=lambda c: c.score, reverse=True)

    if not scored:
        return MatchResponse(
            explanation="Подходящей номенклатуры не найдено — выбрать вручную"
        )

    best = scored[0]
    gap = best.score - scored[1].score if len(scored) > 1 else best.score
    reliable = best.score >= RELIABLE_SCORE and gap >= RELIABLE_GAP

    explanation = (
        f"Рекомендуется: {best.source or 'подбор'} (оценка {best.score})"
        if reliable
        else f"Неоднозначно: оценка {best.score}, вариантов {len(scored)} — проверьте вручную"
    )

    return MatchResponse(
        best=best, reliable=reliable, explanation=explanation, candidates=scored[:5]
    )
