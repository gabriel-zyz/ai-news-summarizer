"""P0 ingestion: list each source, skip URLs already stored, fetch and extract the rest.

Sources run in parallel (one thread each); within a source, pages are fetched one at a time
so we never hit a single site with concurrent requests.
"""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from . import http
from .extract import extract
from .listings import PARSERS
from .models import Article, ListingItem, Source

log = logging.getLogger(__name__)

REGION_TZ = {
    "AU": ZoneInfo("Australia/Sydney"),
    "US": ZoneInfo("America/New_York"),
    "CN": ZoneInfo("Asia/Shanghai"),
    "TW": ZoneInfo("Asia/Taipei"),
}


@dataclass
class SourceResult:
    source_id: str
    listed: int = 0
    new: int = 0
    articles: list[Article] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.listed > 0 and not (self.new and not self.articles)

    def stats(self) -> dict:
        extracted = sum(1 for a in self.articles if a.extra.get("extraction") == "ok")
        return {
            "listed": self.listed,
            "new": self.new,
            "extracted": extracted,
            "errors": self.errors[:5],
        }


def list_source(client, source: Source) -> list[ListingItem]:
    parse = PARSERS[source.kind]
    seen: dict[str, ListingItem] = {}
    for feed_url in source.feeds:
        resp = http.get(client, feed_url)
        for item in parse(source.id, resp.content, str(resp.url)):
            seen.setdefault(item.url, item)
    return list(seen.values())


def fresh(items: list[ListingItem], max_age: timedelta, now: datetime) -> list[ListingItem]:
    """Drop links known to be older than max_age (homepages keep old links around)."""
    cutoff = now - max_age
    return [i for i in items if i.published_at is None or i.published_at >= cutoff]


def ingest_source(
    client,
    source: Source,
    is_known: Callable[[list[str]], set[str]],
    max_per_source: int,
    max_age: timedelta,
    delay: float,
) -> SourceResult:
    result = SourceResult(source.id)
    try:
        items = fresh(list_source(client, source), max_age, datetime.now(UTC))
    except Exception as exc:  # noqa: BLE001 — one broken source must not stop the run
        result.errors.append(f"listing: {exc!r}")
        log.warning("%s: listing failed: %r", source.id, exc)
        return result
    result.listed = len(items)
    known = is_known([i.url for i in items])
    todo = [i for i in items if i.url not in known][:max_per_source]
    result.new = len(todo)

    for item in todo:
        try:
            resp = http.get(client, item.url)
            # Bytes, not resp.text: Chinese pages often declare their charset only in <meta>.
            text, page_date, page_title = extract(resp.content, item.url, REGION_TZ[source.region])
            status = "ok" if text else "empty"
        except Exception as exc:  # noqa: BLE001 — one bad page must not stop the source
            result.errors.append(f"{item.url}: {exc!r}")
            text, page_date, page_title, status = None, None, None, "error"
        result.articles.append(
            Article(
                source_id=source.id,
                url=item.url,
                title=item.title or page_title or "",
                excerpt=item.excerpt,
                content=text,
                # Page metadata is more precise than URL dates and fixes UDN's 1970 feed dates.
                published_at=page_date if _more_precise(page_date, item.published_at)
                else item.published_at,
                language=source.language,
                extra={"extraction": status},
            )
        )
        time.sleep(delay)
    log.info("%s: listed %d, new %d, fetched %d", source.id, result.listed, result.new,
             len(result.articles))
    return result


def _more_precise(page: datetime | None, listed: datetime | None) -> bool:
    if page is None:
        return False
    if listed is None:
        return True
    # URL-derived dates sit at midnight; feed timestamps carry a time of day.
    return listed.time() == datetime.min.time() and page.date() == listed.date()


def run(
    sources: list[Source],
    is_known: Callable[[list[str]], set[str]] = lambda urls: set(),
    max_per_source: int = 40,
    max_age: timedelta = timedelta(days=2),
    delay: float = 0.5,
) -> list[SourceResult]:
    with http.make_client() as client, ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = [
            pool.submit(ingest_source, client, s, is_known, max_per_source, max_age, delay)
            for s in sources
        ]
        return [f.result() for f in futures]
