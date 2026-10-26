import hashlib
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from .ingest.models import Article, Source

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set (see .env.example)")
    return psycopg.connect(url)


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply migrations/NNNN_*.sql in order, each once, each in its own transaction."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    conn.commit()
    done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)
    return applied


def sync_sources(conn: psycopg.Connection, sources: list[Source]) -> None:
    """sources.yaml is the source of truth; sources dropped from it are deactivated, not deleted."""
    with conn.transaction():
        conn.execute("UPDATE sources SET active = false")
        for s in sources:
            conn.execute(
                """
                INSERT INTO sources (id, name, region, language, kind, feeds, active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, region = EXCLUDED.region,
                    language = EXCLUDED.language, kind = EXCLUDED.kind,
                    feeds = EXCLUDED.feeds, active = true
                """,
                (s.id, s.name, s.region, s.language, s.kind, list(s.feeds)),
            )


def known_urls(conn: psycopg.Connection, urls: list[str]) -> set[str]:
    rows = conn.execute("SELECT url FROM articles WHERE url = ANY(%s)", (urls,))
    return {r[0] for r in rows}


def start_run(conn: psycopg.Connection) -> int:
    run_id = conn.execute("INSERT INTO ingest_runs DEFAULT VALUES RETURNING id").fetchone()[0]
    conn.commit()
    return run_id


def finish_run(conn: psycopg.Connection, run_id: int, status: str, stats: dict) -> None:
    conn.execute(
        "UPDATE ingest_runs SET finished_at = now(), status = %s, stats = %s WHERE id = %s",
        (status, Jsonb(stats), run_id),
    )
    conn.commit()


def content_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def insert_articles(conn: psycopg.Connection, articles: list[Article], run_id: int) -> int:
    """Insert new articles. Skips a URL seen before, and text the same source already stored
    under another URL (UDN files one story under several category paths).
    Identical text from different sources (wire copy) is kept: that is signal for clustering.
    """
    inserted = 0
    with conn.transaction():
        for a in articles:
            h = content_hash(a.content)
            cur = conn.execute(
                """
                INSERT INTO articles (source_id, url, title, excerpt, content, content_hash,
                    language, published_at, extraction, run_id)
                SELECT %(source_id)s, %(url)s, %(title)s, %(excerpt)s, %(content)s,
                    %(hash)s::text, %(language)s, %(published_at)s::timestamptz,
                    %(extraction)s, %(run_id)s
                WHERE %(hash)s::text IS NULL OR NOT EXISTS (
                    SELECT 1 FROM articles
                    WHERE source_id = %(source_id)s AND content_hash = %(hash)s::text
                )
                ON CONFLICT (url) DO NOTHING
                """,
                {
                    "source_id": a.source_id, "url": a.url, "title": a.title,
                    "excerpt": a.excerpt, "content": a.content, "hash": h,
                    "language": a.language, "published_at": a.published_at,
                    "extraction": a.extra.get("extraction", "ok"), "run_id": run_id,
                },
            )
            inserted += cur.rowcount
    return inserted
