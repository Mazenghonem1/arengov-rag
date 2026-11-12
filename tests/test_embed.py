import numpy as np
import pytest

from arengov.embed import embed_texts


@pytest.mark.slow
def test_cross_lingual_similarity_and_norm():
    en, ar_same, ar_other = embed_texts(
        [
            "How do I renew my Emirates ID?",
            "كيف أجدد بطاقة الهوية الإماراتية؟",
            "ما هي رسوم تسجيل شركة جديدة في المنطقة الحرة؟",
        ]
    )
    assert en @ ar_same > en @ ar_other
    assert np.linalg.norm(en) == pytest.approx(1.0, abs=1e-4)
