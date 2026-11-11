import json

import httpx
import pytest

from arengov import config, crawl

CAT = "/en/information-and-services/jobs"


def _html(title, links=()):
    body = "".join(f'<a href="{h}">x</a>' for h in links)
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"


# Invented site: category page -> sub-a (chain to depth 5), sub-b (no AR mirror), sub-c.
EN_PAGES = {
    CAT: [
        CAT + "/sub-a",
        "https://u.ae" + CAT + "/sub-b/?x=1#frag",
        CAT + "/sub-c",
        "/en/information-and-services/business/other",  # other category
        "https://example.com/x",
        "mailto:a@example.com",
        CAT + "/file.pdf",
    ],
    CAT + "/sub-a": [CAT + "/sub-a/d2"],
    CAT + "/sub-a/d2": [CAT + "/sub-a/d3"],
    CAT + "/sub-a/d3": [CAT + "/sub-a/d4"],
    CAT + "/sub-a/d4": [CAT + "/sub-a/d5"],  # depth 4 pages don't enqueue depth 5
    CAT + "/sub-a/d5": [],
    CAT + "/sub-b": [],
    CAT + "/sub-c": [],
}


class Site:
    def __init__(self, fail=()):
        self.fail = set(fail)
        self.page_requests = []

    def handler(self, request):
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)
        self.page_requests.append(path)
        if path in self.fail:
            return httpx.Response(503)
        if path in EN_PAGES:
            return httpx.Response(
                200, text=_html(path, EN_PAGES[path]), headers={"content-type": "text/html"}
            )
        ar = path.replace("/ar/", "/en/", 1)
        if path.startswith("/ar/") and ar in EN_PAGES and not ar.endswith("sub-b"):
            return httpx.Response(
                200, text=_html("عنوان " + path), headers={"content-type": "text/html"}
            )
        return httpx.Response(404)

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self.handler), follow_redirects=True)


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(crawl, "_sleep", lambda s: None)
    monkeypatch.setattr(config, "SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(config, "CATEGORIES", ("jobs",))


def _manifest(snap):
    return [json.loads(line) for line in (snap / "manifest.jsonl").read_text("utf-8").splitlines()]


def test_normalize_url():
    base = "https://u.ae/en/a/b"
    assert crawl.normalize_url("c", base) == "https://u.ae/en/a/c"
    assert crawl.normalize_url("/en/x/?q=1#f", base) == "https://u.ae/en/x"
    assert crawl.normalize_url("http://www.u.ae/en/x/", base) == "https://u.ae/en/x"
    assert crawl.normalize_url("https://example.com/en/x", base) is None
    assert crawl.normalize_url("/en/doc.PDF", base) is None
    assert crawl.normalize_url("mailto:a@b.c", base) is None
    assert crawl.normalize_url("javascript:void(0)", base) is None


def test_category_page_id_mirror():
    url = "https://u.ae/en/information-and-services/Jobs/Foo/"
    assert crawl.category_of(url) == "jobs"
    assert crawl.category_of("https://u.ae/en/information-and-services/jobsx") is None
    assert crawl.page_id(url) == "information-and-services/jobs/foo"
    assert crawl.mirror_url("https://u.ae/en/a/b") == "https://u.ae/ar/a/b"
    assert crawl.mirror_url("https://u.ae/ar/a/b") == "https://u.ae/en/a/b"


def test_crawl_scope_depth_and_mirrors():
    site = Site()
    snap = crawl.crawl("t1", client=site.client())
    recs = _manifest(snap)
    en = {r["url"].removeprefix("https://u.ae"): r for r in recs if r["lang"] == "en"}
    assert set(en) == {CAT, CAT + "/sub-a", CAT + "/sub-b", CAT + "/sub-c"} | {
        CAT + f"/sub-a/d{i}" for i in (2, 3, 4)
    }
    assert en[CAT + "/sub-a/d4"]["depth"] == 4
    ar = {r["url"]: r for r in recs if r["lang"] == "ar"}
    sub_a = en[CAT + "/sub-a"]
    assert sub_a["pair_url"] == "https://u.ae/ar" + CAT.removeprefix("/en") + "/sub-a"
    assert ar[sub_a["pair_url"]]["pair_url"] == sub_a["url"]
    assert en[CAT + "/sub-b"]["pair_url"] is None
    assert all(len(r) == 11 for r in recs)
    log = (snap / "crawl.log").read_text().splitlines()
    assert len(log) == len(site.page_requests) + 1  # +1 for robots.txt
    assert all(len(line.split("\t")) == 4 for line in log)


def test_cap(monkeypatch):
    monkeypatch.setattr(config, "CRAWL_MAX_EN_PER_CATEGORY", 2)
    recs = _manifest(crawl.crawl("t2", client=Site().client()))
    assert sum(r["lang"] == "en" for r in recs) == 2


def test_abort_on_consecutive_errors_keeps_manifest():
    site = Site(fail=[CAT + "/sub-a", CAT + "/sub-b", CAT + "/sub-c"])
    with pytest.raises(RuntimeError, match="503"):
        crawl.crawl("t3", client=site.client())
    urls = [r["url"] for r in _manifest(config.SNAPSHOT_ROOT / "t3")]
    assert "https://u.ae" + CAT in urls


def test_resume_makes_no_page_requests():
    crawl.crawl("t4", client=Site().client())
    second = Site()
    crawl.crawl("t4", client=second.client())
    assert second.page_requests == []


def test_diff(tmp_path):
    def write(name, rows):
        d = tmp_path / name
        d.mkdir()
        (d / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        return d

    old = write("old", [{"url": "a", "sha256": "1"}, {"url": "b", "sha256": "1"}])
    new = write("new", [{"url": "b", "sha256": "2"}, {"url": "c", "sha256": "1"}])
    assert crawl.diff(old, new) == {"new": ["c"], "changed": ["b"], "removed": ["a"]}
