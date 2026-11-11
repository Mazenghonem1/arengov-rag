import pytest

from arengov import chunk

META = {"page_id": "a/b", "url": "u", "lang": "en", "pair_url": None, "snapshot_id": "s",
        "category": "jobs"}  # fmt: skip


@pytest.fixture(autouse=True)
def words(monkeypatch):
    monkeypatch.setattr(chunk, "count_tokens", lambda t: len(t.split()))
    monkeypatch.setattr(chunk, "CHUNK_MAX_TOKENS", 20)


def w(n, tag):
    return " ".join(f"{tag}{i}" for i in range(n))


def test_heading_path_and_empty_sections():
    md = "# T\n\n## A\n\nbody a\n\n### A1\n\n## B\n\n### B1\n\nbody b1\n\nbody b1 more"
    cs = chunk.chunk_page("T", md, META)
    assert [c["heading_path"] for c in cs] == ["T > A", "T > B > B1"]
    assert cs[0]["text"] == "T > A\nbody a"
    assert [c["chunk_id"] for c in cs] == ["en:a/b:0", "en:a/b:1"]


def test_intro_before_first_h2_uses_title_only():
    cs = chunk.chunk_page("T", "intro\n\n## A\n\nx", META)
    assert cs[0]["heading_path"] == "T"


def test_limit_and_overlap():
    paras = [w(8, "p"), w(8, "q"), w(8, "r")]
    cs = chunk.chunk_page("T", "\n\n".join(paras), META)
    assert len(cs) >= 2
    assert all(len(c["text"].split()) <= 20 for c in cs)
    assert paras[0] not in cs[1]["text"] and paras[1] in cs[1]["text"]  # last para overlaps


def test_long_sentence_and_paragraph_split():
    long_para = f"{w(5, 'a')}. {w(30, 'b')}. {w(5, 'c')}."
    cs = chunk.chunk_page("T", long_para, META)
    assert all(len(c["text"].split()) <= 20 for c in cs)
    assert "b29" in cs[-1]["text"] or any("b29" in c["text"] for c in cs)


@pytest.mark.slow
def test_real_tokenizer_arabic(monkeypatch):
    monkeypatch.undo()
    assert chunk.count_tokens("يحقّ لكلّ مقيمٍ التقديم") > 0
