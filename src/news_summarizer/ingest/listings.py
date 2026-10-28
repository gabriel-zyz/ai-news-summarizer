"""Turn a feed or listing page into ListingItems. One parser per source kind."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import feedparser
import lxml.html

from .models import ListingItem

CST = timezone(timedelta(hours=8))  # Beijing / Taipei
_TRACKING_PARAMS = re.compile(
    r"^(utm_|fbclid$|gclid$|cmpid$|ocid$|ref$|ftag$|ito$|_?intcmp$|from$|form$)", re.IGNORECASE
)


def canonical_url(url: str) -> str:
    """Drop tracking params and the fragment so the same article dedupes across feeds."""
    url = url.strip()
    # Chinanews sometimes emits the host twice: "https://a.cnhttps://a.cn/path". Keep the last URL.
    url = url[url.rfind("http://") if url.rfind("http://") > 0 else 0 :]
    url = url[url.rfind("https://") if url.rfind("https://") > 0 else 0 :]
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING_PARAMS.match(k)]
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, urlencode(query), ""))


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = lxml.html.fromstring(f"<div>{text}</div>").text_content() if "<" in text else text
    return re.sub(r"\s+", " ", text).strip()


def _plausible(dt: datetime | None) -> datetime | None:
    # UDN's feed reports 1970 dates; treat anything that old as unknown.
    return dt if dt and dt.year >= 2000 else None


def parse_rss(source_id: str, body: bytes, base_url: str) -> list[ListingItem]:
    feed = feedparser.parse(body)
    items = []
    for e in feed.entries:
        link = e.get("link")
        if not link:
            continue
        struct = e.get("published_parsed") or e.get("updated_parsed")
        published = datetime(*struct[:6], tzinfo=UTC) if struct else None
        items.append(
            ListingItem(
                source_id=source_id,
                url=canonical_url(urljoin(base_url, link)),
                title=_clean(e.get("title")),
                excerpt=_clean(e.get("summary")) or None,
                published_at=_plausible(published),
            )
        )
    return items


def _anchors(body: bytes, base_url: str) -> list[tuple[str, str]]:
    # lxml falls back to Latin-1 for bytes without a <meta charset>; try UTF-8 first.
    try:
        doc = lxml.html.fromstring(body.decode("utf-8"))
    except UnicodeDecodeError:
        doc = lxml.html.fromstring(body)
    doc.make_links_absolute(base_url)
    return [(a.get("href", ""), _clean(a.text_content())) for a in doc.iter("a")]


def _from_anchors(
    source_id: str, body: bytes, base_url: str, pattern: re.Pattern, to_date: Callable
) -> list[ListingItem]:
    """Homepage scrape: keep article links matching `pattern`; the date comes from the URL.

    A link often appears several times (image + headline); keep the longest anchor text.
    """
    best: dict[str, ListingItem] = {}
    for href, text in _anchors(body, base_url):
        m = pattern.match(href)
        if not m:
            continue
        url = canonical_url(href)
        if url not in best or len(text) > len(best[url].title):
            best[url] = ListingItem(source_id, url, text, published_at=to_date(m))
    # Drop links with no headline text (image-only links that never got a text twin).
    return [i for i in best.values() if len(i.title) >= 4]


XINHUA_RE = re.compile(
    r"^https?://www\.news\.cn/(?!photo/)[a-z0-9/]+/(\d{4})(\d{2})(\d{2})/[0-9a-f]{32}/c\.html$"
)
PEOPLE_RE = re.compile(
    r"^https?://(?!pic\.)[a-z]+\.people\.com\.cn/n1/(\d{4})/(\d{2})(\d{2})/c\d+-\d+\.html$"
)


def _ymd(m: re.Match) -> datetime:
    return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=CST)


def parse_xinhua(source_id: str, body: bytes, base_url: str) -> list[ListingItem]:
    return _from_anchors(source_id, body, base_url, XINHUA_RE, _ymd)


def parse_people(source_id: str, body: bytes, base_url: str) -> list[ListingItem]:
    return _from_anchors(source_id, body, base_url, PEOPLE_RE, _ymd)


def parse_cctv(source_id: str, body: bytes, base_url: str) -> list[ListingItem]:
    """news_1.jsonp is a JSONP list: news({"data": {"list": [...]}})."""
    text = body.decode("utf-8")
    payload = json.loads(text[text.index("(") + 1 : text.rindex(")")])
    items = []
    for row in payload["data"]["list"]:
        published = datetime.strptime(row["focus_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
        items.append(
            ListingItem(
                source_id=source_id,
                url=canonical_url(row["url"]),
                title=_clean(row["title"]),
                excerpt=_clean(row.get("brief")) or None,
                published_at=published,
            )
        )
    return items


def parse_udn(source_id: str, body: bytes, base_url: str) -> list[ListingItem]:
    """UDN's breaking-news JSON (its RSS feeds return empty items since 2026-10).

    `time.dateTime` is Taipei local time mislabelled as Z, so parse the plain `time.date`.
    Paywalled stories (content_level other than 開放閱讀) are skipped.
    """
    items = []
    for row in json.loads(body)["lists"]:
        if row.get("content_level") != "開放閱讀" or row.get("is_video"):
            continue
        published = datetime.strptime(row["time"]["date"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)
        items.append(
            ListingItem(
                source_id=source_id,
                url=canonical_url(urljoin(base_url, row["titleLink"]).split("?")[0]),
                title=_clean(row["title"]),
                excerpt=_clean(row.get("paragraph")) or None,
                published_at=published,
            )
        )
    return items


_MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
_URL_DATES = [
    # /2026-10-28/  /2026/10/28/  /2026/oct/28/  /20261028/  -20261028-  /2026/1028/  /2026/10-28/
    re.compile(r"/(\d{4})-(\d{2})-(\d{2})/"),
    re.compile(r"/(\d{4})/(\d{2})/(\d{2})/"),
    re.compile(r"/(\d{4})/([a-z]{3})/(\d{2})/"),
    re.compile(r"[/-](\d{4})(\d{2})(\d{2})[/-]"),
    re.compile(r"/(\d{4})/(\d{2})(\d{2})/"),
    re.compile(r"/(\d{4})/(\d{2})-(\d{2})/"),
    re.compile(r"/(\d{4})(\d{2})(\d{2})\d{4}\.aspx$"),  # CNA: /202610280137.aspx
]


def url_date(url: str) -> datetime | None:
    """Publication date encoded in an article URL, if any (local midnight, Beijing/Taipei zone
    is close enough: it is only used to drop stale links)."""
    for pattern in _URL_DATES:
        m = pattern.search(url)
        if not m:
            continue
        month = _MONTHS.index(m[2]) + 1 if m[2].isalpha() else int(m[2])
        try:
            return datetime(int(m[1]), month, int(m[3]), tzinfo=CST)
        except ValueError:
            continue
    return None


_TIME_TOKEN = re.compile(r"(?:^|\s)\d{1,2}:\d{2}(?:\s|$)")


def _headline(text: str) -> str:
    """Anchor text minus list decorations: a leading section and time ("政治13:44標題",
    "14:17 標題"), a time followed by a teaser ("標題 14:08 摘要…"), reading-time suffixes
    ("…2 min read") and comment-count links ("…… comments")."""
    if re.fullmatch(r"[\W\d]*comments?", text, re.IGNORECASE):
        return ""
    text = re.sub(r"^\D{0,6}?\d{1,2}:\d{2}\s*", "", text)
    m = _TIME_TOKEN.search(text)
    if m and m.start() > 0:
        text = text[: m.start()]
    return re.sub(r"\d+ min(ute)?s? read$", "", text).strip()


def parse_frontpage(
    source_id: str,
    body: bytes,
    base_url: str,
    pattern: re.Pattern,
    limit: int = 10,
    max_age: timedelta = timedelta(days=3),
    now: datetime | None = None,
) -> list[ListingItem]:
    """Headlines in the order the homepage shows them (DOM order = editorial prominence).

    Rank is the position of a URL's first appearance. Links whose URL date is older than
    `max_age` are dropped before ranking (pinned specials, stale blocks). A URL's headline is
    its first anchor text of 6+ characters (image links have none; later ones are often
    teasers). It is only a fallback: the UI prefers the article page's own title.
    """
    cutoff = (now or datetime.now(UTC)) - max_age
    order: list[str] = []
    titles: dict[str, str] = {}
    for href, text in _anchors(body, base_url):
        if not href.startswith("http"):
            continue
        url = canonical_url(href)
        if not pattern.match(url):
            continue
        headline = _headline(text)
        if url not in titles:
            order.append(url)
            titles[url] = ""
        if len(titles[url]) < 6 and len(headline) >= 6:
            titles[url] = headline
    items = []
    for url in order:
        published = url_date(url)
        if published and published < cutoff:
            continue
        if not titles[url]:
            continue
        items.append(ListingItem(source_id, url, titles[url], published_at=published))
    return items[:limit]


PARSERS = {
    "rss": parse_rss,
    "xinhua": parse_xinhua,
    "people": parse_people,
    "cctv": parse_cctv,
    "udn": parse_udn,
}
