from datetime import UTC, datetime, timedelta

import pytest

from news_summarizer.ingest import pipeline
from news_summarizer.ingest.listings import CST
from news_summarizer.ingest.models import ListingItem, load_sources


def test_sources_cover_four_regions_with_four_outlets_each():
    sources = load_sources()
    assert len({s.id for s in sources}) == 16
    for region in ("AU", "US", "CN", "TW"):
        assert sum(s.region == region for s in sources) == 4


def test_fresh_drops_old_but_keeps_undated():
    now = datetime(2026, 10, 26, 12, tzinfo=UTC)
    items = [
        ListingItem("s", "a", "old", published_at=now - timedelta(days=30)),
        ListingItem("s", "b", "new", published_at=now - timedelta(hours=1)),
        ListingItem("s", "c", "undated"),
    ]
    assert [i.url for i in pipeline.fresh(items, timedelta(days=2), now)] == ["b", "c"]


def test_page_date_replaces_midnight_url_date_only():
    url_date = datetime(2026, 10, 26, tzinfo=CST)
    page_date = datetime(2026, 10, 26, 9, 30, tzinfo=CST)
    feed_date = datetime(2026, 10, 26, 1, 30, tzinfo=UTC)
    assert pipeline._more_precise(page_date, url_date)
    assert pipeline._more_precise(page_date, None)
    assert not pipeline._more_precise(page_date, feed_date)
    assert not pipeline._more_precise(None, url_date)


@pytest.mark.live
@pytest.mark.parametrize("source", load_sources(), ids=lambda s: s.id)
def test_live_source_lists_articles(source):
    from news_summarizer.ingest import http

    with http.make_client() as client:
        items = pipeline.fresh(
            pipeline.list_source(client, source), timedelta(days=2), datetime.now(UTC)
        )
    assert len(items) >= 5
