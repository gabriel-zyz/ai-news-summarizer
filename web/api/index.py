"""Read-only API for the web app, deployed as a Vercel Python function.

The ingestion pipeline (repo root, GitHub Actions) writes to Postgres; this only reads.
Local dev: `uvicorn api.index:app --port 8000` from web/, with DATABASE_URL set.
"""

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

app = FastAPI(title="AI News Summarizer API", docs_url="/api/docs", openapi_url="/api/openapi.json")

REGION_ORDER = ["AU", "US", "CN", "TW"]
# Same zones the pipeline uses for bare page dates (src/news_summarizer/ingest/pipeline.py).
REGION_TZ = {
    "AU": ZoneInfo("Australia/Sydney"),
    "US": ZoneInfo("America/New_York"),
    "CN": ZoneInfo("Asia/Shanghai"),
    "TW": ZoneInfo("Asia/Taipei"),
}
EXCERPT_CHARS = 160  # public demo shows short excerpts only, never full text


class Headline(BaseModel):
    rank: int
    title: str
    url: str
    published_at: datetime | None
    # True when the outlet only gave a date (stored as local midnight): show the date, not
    # "15 hours ago".
    date_only: bool
    excerpt: str | None


class Outlet(BaseModel):
    id: str
    name: str
    region: str
    language: str
    captured_at: datetime
    headlines: list[Headline]


class FrontPages(BaseModel):
    outlets: list[Outlet]


# Latest snapshot per outlet, its items in rank order, with the article's own title when
# the article page has been fetched (homepage anchor text is only a fallback).
FRONTPAGES_SQL = """
WITH latest AS (
    SELECT DISTINCT ON (source_id) id, source_id, captured_at
    FROM frontpage_snapshots
    ORDER BY source_id, captured_at DESC
)
SELECT s.id, s.name, s.region, s.language, l.captured_at,
       i.rank, i.url,
       COALESCE(NULLIF(a.title, ''), i.title) AS title,
       a.published_at,
       left(COALESCE(a.excerpt, a.content), %(chars)s) AS excerpt
FROM sources s
JOIN latest l ON l.source_id = s.id
JOIN frontpage_items i ON i.snapshot_id = l.id
LEFT JOIN articles a ON a.url = i.url
WHERE s.active
ORDER BY array_position(%(regions)s::text[], s.region), s.id, i.rank
"""


def _connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(500, "DATABASE_URL is not set")
    return psycopg.connect(url, row_factory=dict_row)


def _excerpt(text: str | None, title: str) -> str | None:
    """Short excerpt without the headline, which article bodies often start with."""
    if not text:
        return None
    text = " ".join(text.split())
    if text.startswith(title):
        text = text[len(title):].lstrip(" ：:—-")
    return text or None


def _is_local_midnight(ts: datetime | None, region: str) -> bool:
    return ts is not None and ts.astimezone(REGION_TZ[region]).time() == time(0)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/frontpages")
def frontpages() -> FrontPages:
    with _connect() as conn:
        rows = conn.execute(
            FRONTPAGES_SQL, {"chars": EXCERPT_CHARS, "regions": REGION_ORDER}
        ).fetchall()
    outlets: dict[str, Outlet] = {}
    for r in rows:
        outlet = outlets.get(r["id"])
        if outlet is None:
            outlet = outlets[r["id"]] = Outlet(
                id=r["id"], name=r["name"], region=r["region"], language=r["language"],
                captured_at=r["captured_at"], headlines=[],
            )
        excerpt = _excerpt(r["excerpt"], r["title"])
        outlet.headlines.append(
            Headline(
                rank=r["rank"], title=r["title"], url=r["url"],
                published_at=r["published_at"],
                date_only=_is_local_midnight(r["published_at"], r["region"]),
                excerpt=excerpt,
            )
        )
    return FrontPages(outlets=list(outlets.values()))
