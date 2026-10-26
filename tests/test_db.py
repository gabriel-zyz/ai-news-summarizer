"""Runs against a real Postgres when TEST_DATABASE_URL is set (the database is wiped)."""

import os
from datetime import UTC, datetime

import psycopg
import pytest

from news_summarizer import db
from news_summarizer.ingest.models import Article, load_sources

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def conn():
    with psycopg.connect(URL) as c:
        c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        c.commit()
        yield c


def test_migrate_is_idempotent(conn):
    assert db.migrate(conn) == ["0001_init.sql"]
    assert db.migrate(conn) == []


def test_insert_dedupes_by_url_and_tracks_run(conn):
    db.migrate(conn)
    db.sync_sources(conn, load_sources())
    run_id = db.start_run(conn)
    a = Article("npr", "https://npr.test/a", "T", None, "body  text", datetime.now(UTC), "en",
                {"extraction": "ok"})
    assert db.insert_articles(conn, [a, a], run_id) == 1
    assert db.known_urls(conn, ["https://npr.test/a", "https://npr.test/b"]) == {
        "https://npr.test/a"
    }
    db.finish_run(conn, run_id, "ok", {"inserted": 1})
    status, stats = conn.execute(
        "SELECT status, stats FROM ingest_runs WHERE id = %s", (run_id,)
    ).fetchone()
    assert (status, stats) == ("ok", {"inserted": 1})


def test_same_text_skipped_within_source_but_kept_across_sources(conn):
    db.migrate(conn)
    db.sync_sources(conn, load_sources())
    run_id = db.start_run(conn)

    def art(source, url):
        return Article(source, url, "T", None, "同一篇新華社通稿", None, "zh", {"extraction": "ok"})

    assert db.insert_articles(conn, [
        art("udn", "https://udn.com/news/story/6656/1"),
        art("udn", "https://udn.com/news/story/124652/1"),
        art("xinhua", "https://www.news.cn/a"),
        art("people", "http://people.test/a"),
    ], run_id) == 3


def test_sync_sources_deactivates_removed(conn):
    db.migrate(conn)
    sources = load_sources()
    db.sync_sources(conn, sources)
    db.sync_sources(conn, sources[1:])
    inactive = conn.execute("SELECT id FROM sources WHERE NOT active").fetchall()
    assert inactive == [(sources[0].id,)]
