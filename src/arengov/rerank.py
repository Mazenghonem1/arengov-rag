import functools

import torch
from sentence_transformers import CrossEncoder

from arengov import config


@functools.cache
def _model() -> CrossEncoder:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return CrossEncoder(config.RERANK_MODEL, max_length=config.RERANK_MAX_LENGTH, device=device)


def rerank(query, chunks, idxs):
    pairs = [(query, chunks[i]["text"]) for i in idxs]
    scores = _model().predict(pairs, batch_size=16, activation_fn=torch.nn.Sigmoid())
    return sorted(zip(idxs, (float(s) for s in scores), strict=True), key=lambda t: -t[1])
