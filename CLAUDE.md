# AI News Summarizer v2

Cross-language, claim-level comparison of how AU / US / mainland China / Taiwan outlets report
the same event. Phases and status are in README.md.

## Layout

- `src/news_summarizer/sources.yaml` — the 16 sources; edit here, `ans migrate` syncs to the DB.
- `src/news_summarizer/ingest/` — `listings.py` (one parser per source kind), `extract.py`
  (trafilatura + per-site body extractors), `pipeline.py` (orchestration), `http.py`.
- `src/news_summarizer/db.py` + `migrations/NNNN_*.sql` — plain SQL migrations, psycopg 3.
- `src/news_summarizer/cli.py` — `ans migrate`, `ans ingest [--dry-run]`.

## Rules

- Python 3.12+, uv. Run `uv run ruff check .` and `uv run pytest` before committing.
- Tests are offline by default (fixtures in `tests/fixtures/`). `-m live` hits real sites;
  `TEST_DATABASE_URL` enables DB tests (the database is wiped).
- Crawl politely: honest user agent, one request at a time per site, never work around bot
  blocks or paywalls — drop the source instead.
- Never commit `.env` or full article text fixtures beyond what a test needs.
- The user writes, or reviews line by line, the clustering, claim alignment and eval code
  (P1–P2). Explain design choices there rather than just generating code.
