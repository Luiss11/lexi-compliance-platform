from dataclasses import dataclass

from app.rag.guard import FALLBACK_MESSAGE, apply_cutoff


@dataclass
class FakeHit:
    dense_score: float


def test_fallback_message_is_exact():
    assert FALLBACK_MESSAGE == "No se encontró documento de soporte autorizado en la base de conocimiento."


def test_cutoff_keeps_only_scores_at_or_above_075():
    hits = [FakeHit(0.86), FakeHit(0.75), FakeHit(0.749), FakeHit(0.61)]
    kept = apply_cutoff(hits, cutoff=0.75)
    assert [h.dense_score for h in kept] == [0.86, 0.75]


def test_cutoff_empty_when_all_below():
    assert apply_cutoff([FakeHit(0.6), FakeHit(0.7)], cutoff=0.75) == []
