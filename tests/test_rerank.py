import pytest

from arengov.eval_retrieval import choose_tau


def test_choose_tau_picks_best_f1():
    rows = [(0.1, True), (0.2, True), (0.3, True), (0.8, False), (0.9, False), (0.95, False)]
    best = choose_tau(rows)
    assert best["tau"] == 0.8 and best["f1"] == 1.0 and best["safe"]


def test_choose_tau_unsafe_when_it_refuses_answerable():
    rows = [(0.1, False), (0.2, True), (0.3, False), (0.4, False), (0.9, False), (0.95, False)]
    assert not choose_tau(rows)["safe"]


@pytest.mark.slow
def test_rerank_prefers_relevant_passage():
    from arengov.rerank import rerank

    chunks = [
        {"text": "رسوم تجديد الهوية الإماراتية وطريقة الدفع عبر الموقع"},
        {"text": "Recipe for baking chocolate cake with flour and eggs"},
    ]
    out = rerank("كم رسوم تجديد الهوية؟", chunks, [1, 0])
    assert out[0][0] == 0 and 0 <= out[1][1] < out[0][1] <= 1
