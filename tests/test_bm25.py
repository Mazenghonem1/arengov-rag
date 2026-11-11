import math

import numpy as np

from arengov.bm25 import BM25

DOCS = [["visa", "renew", "visa"], ["license", "renew"], ["license", "trade", "fee", "fee"]]


def test_hand_computed_score():
    # N=3, avgdl=(3+2+4)/3=3, doc0 dl=3 -> k1*(1-b+b*dl/avgdl) = 1.5
    idf_visa = math.log((3 - 1 + 0.5) / (1 + 0.5) + 1)  # df=1
    idf_renew = math.log((3 - 2 + 0.5) / (2 + 0.5) + 1)  # df=2
    want = idf_visa * 2 * 2.5 / (2 + 1.5) + idf_renew * 1 * 2.5 / (1 + 1.5)
    hits = BM25(DOCS, 1.5, 0.75).search(["visa", "renew"], 10)
    assert hits[0][0] == 0
    assert math.isclose(hits[0][1], want)


def test_order_zero_mask_and_dedup():
    bm = BM25(DOCS)
    # doc1 has renew+license; doc0 renew only; doc2 has neither renew -> trade only
    ranked = [i for i, _ in bm.search(["renew", "license"], 10)]
    assert ranked[0] == 1
    # same tf, shorter doc wins (length normalization); doc2 has score 0 so is absent
    assert [i for i, _ in bm.search(["renew"], 10)] == [1, 0]
    masked = bm.search(["renew"], 10, mask=np.array([False, True, True]))
    assert [i for i, _ in masked] == [1]
    assert bm.search(["visa", "visa"], 10) == bm.search(["visa"], 10)
