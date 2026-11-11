import math
from collections import Counter, defaultdict

import numpy as np

from arengov import config


class BM25:
    def __init__(self, docs_tokens, k1=config.BM25_K1, b=config.BM25_B):
        self.k1, self.b = k1, b
        self.N = len(docs_tokens)
        self.doc_len = np.array([len(d) for d in docs_tokens], dtype=float)
        self.avgdl = self.doc_len.mean() if self.N else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, doc in enumerate(docs_tokens):
            for term, tf in Counter(doc).items():
                self.postings[term].append((i, tf))
        self.idf = {
            t: math.log((self.N - len(p) + 0.5) / (len(p) + 0.5) + 1)
            for t, p in self.postings.items()
        }

    def search(self, query_tokens, top_n, mask=None):
        scores = np.zeros(self.N)
        for term in set(query_tokens):
            for i, tf in self.postings.get(term, ()):
                norm = self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
        if mask is not None:
            scores[~mask] = 0.0
        idxs = np.flatnonzero(scores > 0)
        idxs = idxs[np.lexsort((idxs, -scores[idxs]))][:top_n]  # score desc, idx asc
        return [(int(i), float(scores[i])) for i in idxs]
