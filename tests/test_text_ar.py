import pytest

from arengov.text_ar import detect_lang, normalize_ar, tokenize


@pytest.mark.parametrize(
    ("src", "want"),
    [
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ٱ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
        ("ی", "ي"),
        ("ک", "ك"),
        ("مُحَمَّد", "محمد"),
        ("اٰ", "ا"),
        ("كـــتاب", "كتاب"),
        ("٠١٢٣٤٥٦٧٨٩", "0123456789"),
        ("۰۱۲۳۴۵۶۷۸۹", "0123456789"),
        ("ؤ", "ؤ"),
        ("ئ", "ئ"),
    ],
)
def test_normalize_ar(src, want):
    assert normalize_ar(src) == want


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("تجديد الإقامة", "ar"),
        ("renew residence", "en"),
        ("how to renew الإقامة", "en"),
        ("ما هي شروط الإقامة الذهبية golden visa", "ar"),
        ("12345", "en"),
        ("", "en"),
    ],
)
def test_detect_lang(text, want):
    assert detect_lang(text) == want


def test_tokenize_arabic_diacritics_and_article():
    # diacritics don't split the word; the definite article is stemmed off
    assert tokenize("الإقَامَةُ") == tokenize("الاقامه")
    assert tokenize("الإقامة") == ["اقامه"]  # article gone, hamza and ta marbuta folded


def test_tokenize_english_stems_and_stopwords():
    assert tokenize("licenses") == tokenize("license")
    assert tokenize("how to renew the visa") == tokenize("renew visa")


def test_tokenize_no_norm_keeps_variants():
    assert tokenize("أحمد", normalize=False) != tokenize("احمد", normalize=False)
    assert tokenize("أحمد") == tokenize("احمد")
    assert tokenize("licenses", normalize=False) == ["licenses"]
