from pathlib import Path

from arengov.clean import clean_html

FIX = Path(__file__).parent / "fixtures"


def test_clean_en():
    title, md = clean_html((FIX / "uae_en.html").read_text("utf-8"))
    assert title == "Blue Widget Permits"
    assert "### Who can apply" in md
    assert "- Adults over 18" in md
    assert "- Holders of a valid gadget card" in md
    assert "Type: Standard; Cost: 10 quatloos" in md
    assert "Type: Express; Cost: 25 quatloos" in md
    assert "Type; Cost" not in md and "Type | Cost" not in md  # header row is not a data row
    for noise in ("NAVNOISE", "BREADCRUMBNOISE", "FEEDBACKNOISE", "TOPICNAVNOISE", "FOOTERNOISE",
                  "SCRIPTNOISE", "1 Jan 2026", "http"):  # fmt: skip
        assert noise not in md


def test_clean_ar():
    title, md = clean_html((FIX / "uae_ar.html").read_text("utf-8"))
    assert title == "تصاريح الودجت الأزرق"
    assert "### شروط التقديم" in md
    assert "- حاملو بطاقة الأدوات سارية" in md
    assert "النوع: عادي; التكلفة: ١٠ كواتلو" in md
    for noise in ("ضجيج", "http"):
        assert noise not in md


def test_missing_container():
    assert clean_html("<html><body><p>hi</p></body></html>") == ("", "")
