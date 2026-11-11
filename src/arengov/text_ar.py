import re

import snowballstemmer

_AR_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
_DIACRITICS = re.compile("[ً-ْٰـ]")  # harakat, dagger alef, tatweel
_AR_MAP = str.maketrans(
    {
        **dict.fromkeys("أإآٱ", "ا"),
        "ى": "ي",
        "ة": "ه",
        "ی": "ي",
        "ک": "ك",
        **{chr(0x0660 + i): str(i) for i in range(10)},
        **{chr(0x06F0 + i): str(i) for i in range(10)},
    }
)
EN_STOPWORDS = frozenset(
    "a an and are as at be by can do for from how i in is it my of on or the to what when "
    "where which who with you your".split()
)
_AR_STEM = snowballstemmer.stemmer("arabic")
_EN_STEM = snowballstemmer.stemmer("english")


def is_arabic_char(c: str) -> bool:
    o = ord(c)
    return c.isalpha() and any(lo <= o <= hi for lo, hi in _AR_RANGES)


def detect_lang(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    return "ar" if sum(map(is_arabic_char, letters)) / len(letters) >= 0.5 else "en"


def normalize_ar(text: str) -> str:
    return _DIACRITICS.sub("", text).translate(_AR_MAP)


def tokenize(text: str, normalize: bool = True) -> list[str]:
    text = _DIACRITICS.sub("", text).lower()  # otherwise \w splits words at diacritics
    out = []
    for tok in re.findall(r"[^\W_]+", text):
        if any(is_arabic_char(c) for c in tok):
            out.append(_AR_STEM.stemWord(normalize_ar(tok)) if normalize else tok)
        elif tok not in EN_STOPWORDS:
            out.append(_EN_STEM.stemWord(tok) if normalize else tok)
    return out
