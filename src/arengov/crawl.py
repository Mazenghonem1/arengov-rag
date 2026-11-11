"""Polite single-threaded BFS crawler: EN pages per category plus their AR mirrors."""

import hashlib
import json
import re
import time
import urllib.robotparser
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from arengov import config

_sleep = time.sleep  # module-level so tests can patch it
_SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx", ".zip")


def normalize_url(href, base):
    u = urlsplit(urljoin(base, href.strip()))
    if u.scheme not in ("http", "https") or u.hostname not in ("u.ae", "www.u.ae"):
        return None
    path = u.path.rstrip("/")
    if path.lower().endswith(_SKIP_EXT):
        return None
    return config.BASE_URL + path  # query and fragment dropped


def category_of(url):
    path = urlsplit(url).path.lower().rstrip("/")
    for cat in config.CATEGORIES:
        root = f"/en/information-and-services/{cat}"
        if path == root or path.startswith(root + "/"):
            return cat
    return None


def mirror_url(url):
    return re.sub(
        r"^(https://u\.ae)/(en|ar)\b",
        lambda m: f"{m[1]}/{'ar' if m[2].lower() == 'en' else 'en'}",
        url,
    )


def page_id(url):
    path = urlsplit(url).path.lower().rstrip("/")
    return re.sub(r"^/(en|ar)(?=/|$)", "", path).lstrip("/")


def _now(timespec="seconds"):
    return datetime.now(UTC).isoformat(timespec=timespec)


class _Session:
    """Every request goes through get(): sleeps first, logs, and aborts on repeated errors."""

    def __init__(self, client, log_path):
        self.client = client
        self.log_path = log_path
        self.requests = 0
        self.recent_errors = []  # statuses of the current run of consecutive errors

    def get(self, url):
        _sleep(config.CRAWL_DELAY_S)
        started, t0 = _now("milliseconds"), time.monotonic()
        try:
            resp = self.client.get(url)
            status = resp.status_code
        except httpx.HTTPError:
            resp, status = None, 0
        ms = round((time.monotonic() - t0) * 1000)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"{started}\t{status}\t{ms}\t{url}\n")
        self.requests += 1
        if status in (0, 403, 429) or status >= 500:
            self.recent_errors.append(status)
            if len(self.recent_errors) >= config.CRAWL_MAX_CONSECUTIVE_ERRORS:
                raise RuntimeError(
                    f"aborting after {len(self.recent_errors)} consecutive errors, "
                    f"last statuses: {self.recent_errors[-3:]}"
                )
        else:
            self.recent_errors = []
        return resp


def _load_robots(session):
    resp = session.get(f"{config.BASE_URL}/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    if resp is not None and resp.status_code == 200:
        rp.parse(resp.text.splitlines())
    elif resp is None or resp.status_code != 404:
        raise RuntimeError("robots.txt is unavailable (not 200/404); not crawling blind")
    else:
        rp.parse([])  # 404 = no rules = allow all
    return rp


def _fetch_page(session, robots, url):
    """Return the response only for an allowed 200 HTML page, else None."""
    if not robots.can_fetch(config.USER_AGENT, url):
        return None
    resp = session.get(url)
    if resp is None or resp.status_code != 200:
        return None
    return resp if "html" in resp.headers.get("content-type", "") else None


def _title(soup):
    return soup.title.get_text(strip=True) if soup.title else ""


def _record(url, lang, body, depth, cat, pair_url):
    return {
        "url": url,
        "lang": lang,
        "page_id": page_id(url),
        "pair_url": pair_url,
        "category": cat,
        "depth": depth,
        "title": _title(BeautifulSoup(body, "lxml")),
        "fetched_at": _now(),
        "http_status": 200,
        "sha256": hashlib.sha256(body).hexdigest(),
        # relative to the snapshot dir
        "raw_path": f"raw/{hashlib.sha1(url.encode()).hexdigest()}.html",
    }


def _store(snap, rec, body):
    (snap / rec["raw_path"]).write_bytes(body)
    with (snap / "manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _load_manifest(path):
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    return {r["url"]: r for r in map(json.loads, lines) if r}


def _crawl_category(cat, session, robots, done, snap, seen):
    stats = {"en": 0, "ar": 0, "missing_ar": 0}
    queue = deque([(f"{config.BASE_URL}/en/information-and-services/{cat}", 0)])
    while queue and stats["en"] < config.CRAWL_MAX_EN_PER_CATEGORY:
        url, depth = queue.popleft()
        if url.lower() in seen:
            continue
        seen.add(url.lower())
        rec = done.get(url)
        if rec:  # resume: read the cached page instead of fetching
            body = (snap / rec["raw_path"]).read_bytes()
        else:
            resp = _fetch_page(session, robots, url)
            # a redirect that leaves the category means we skip the page
            if resp is None or category_of(str(resp.url)) != cat:
                continue
            body = resp.content
            mirror = mirror_url(url)
            ar_resp = _fetch_page(session, robots, mirror)
            if ar_resp is not None and page_id(str(ar_resp.url)) != page_id(url):
                ar_resp = None
            # EN line is written after the mirror fetch because pair_url is only known then
            rec = _record(url, "en", body, depth, cat, mirror if ar_resp else None)
            _store(snap, rec, body)
            if ar_resp is not None:
                _store(
                    snap, _record(mirror, "ar", ar_resp.content, depth, cat, url), ar_resp.content
                )
        stats["en"] += 1
        stats["ar" if rec["pair_url"] else "missing_ar"] += 1
        if depth < config.CRAWL_MAX_DEPTH:
            for a in BeautifulSoup(body, "lxml").find_all("a", href=True):
                n = normalize_url(a["href"], url)
                if n and category_of(n) == cat:
                    queue.append((n, depth + 1))
    return stats


def crawl(snapshot_id, client=None):
    snap = config.SNAPSHOT_ROOT / snapshot_id
    (snap / "raw").mkdir(parents=True, exist_ok=True)
    done = _load_manifest(snap / "manifest.jsonl")
    own_client = client is None
    if own_client:
        client = httpx.Client(
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.CRAWL_TIMEOUT_S,
            follow_redirects=True,
        )
    t0 = time.monotonic()
    try:
        session = _Session(client, snap / "crawl.log")
        robots = _load_robots(session)
        seen = set()
        stats = {
            cat: _crawl_category(cat, session, robots, done, snap, seen)
            for cat in config.CATEGORIES
        }
    finally:
        if own_client:
            client.close()
    for cat, s in stats.items():
        print(f"{cat}: EN {s['en']}, AR {s['ar']}, AR missing {s['missing_ar']}")
    print(f"requests: {session.requests}, elapsed: {time.monotonic() - t0:.0f}s, snapshot: {snap}")
    return snap


def diff(old_dir, new_dir):
    def hashes(d):
        return {u: r["sha256"] for u, r in _load_manifest(Path(d) / "manifest.jsonl").items()}

    old, new = hashes(old_dir), hashes(new_dir)
    return {
        "new": sorted(new.keys() - old.keys()),
        "changed": sorted(u for u in new.keys() & old.keys() if new[u] != old[u]),
        "removed": sorted(old.keys() - new.keys()),
    }
