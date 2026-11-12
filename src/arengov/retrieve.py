import numpy as np

from arengov import config


def dense_search(qvec, embeddings, top_n, mask=None):
    # vectors are L2-normalized, so the dot product is the cosine similarity
    scores = embeddings @ qvec
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)
    n = min(top_n, int(np.isfinite(scores).sum()))
    if n == 0:
        return []
    top = np.argpartition(-scores, n - 1)[:n]
    top = sorted(top.tolist(), key=lambda i: (-scores[i], i))
    return [(i, float(scores[i])) for i in top]


def rrf(rankings, k=config.RRF_K):
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, 1):
            fused[idx] = fused.get(idx, 0.0) + 1 / (k + rank)
    return sorted(fused.items(), key=lambda t: (-t[1], t[0]))
