import functools

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from arengov import config


@functools.cache
def _model() -> SentenceTransformer:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(config.EMBED_MODEL, device=device)
    m.max_seq_length = 512
    return m


def device() -> str:
    return str(_model().device)


def embed_texts(texts: list[str], batch_size: int = 16) -> np.ndarray:
    return (
        _model()
        .encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
        )
        .astype(np.float32)
    )


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]
