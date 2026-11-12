import numpy as np
import pytest

from arengov.retrieve import dense_search, rrf


def test_rrf_fuses_ranks():
    fused = rrf([[10, 20, 30], [20, 40]], k=60)
    out = dict(fused)
    assert out[20] == pytest.approx(1 / 62 + 1 / 61)
    assert out[10] == pytest.approx(1 / 61)
    assert out[40] == pytest.approx(1 / 62)
    assert out[30] == pytest.approx(1 / 63)
    assert [i for i, _ in fused] == [20, 10, 40, 30]


def test_rrf_ties_by_idx():
    assert [i for i, _ in rrf([[5], [3]])] == [3, 5]


def test_dense_search_and_mask():
    emb = np.array([[1, 0, 0], [0, 1, 0], [0.8, 0.6, 0], [0, 0, 1]], dtype=np.float32)
    q = np.array([1, 0, 0], dtype=np.float32)
    assert [i for i, _ in dense_search(q, emb, 3)] == [0, 2, 1]
    mask = np.array([False, True, True, True])
    res = dense_search(q, emb, 3, mask)
    assert [i for i, _ in res] == [2, 1, 3]
    assert res[0][1] == pytest.approx(0.8)
    assert dense_search(q, emb, 3, np.zeros(4, dtype=bool)) == []


def test_collapse_pairs_keeps_first_language():
    from arengov.retrieve import collapse_pairs

    chunks = [
        {"page_id": "p1", "lang": "en"},
        {"page_id": "p1", "lang": "ar"},
        {"page_id": "p2", "lang": "ar"},
        {"page_id": "p1", "lang": "en"},
        {"page_id": "p3", "lang": "en"},
    ]
    ranked = [(i, 1.0 - i / 10) for i in range(5)]
    assert [i for i, _ in collapse_pairs(ranked, chunks)] == [0, 2, 3, 4]
