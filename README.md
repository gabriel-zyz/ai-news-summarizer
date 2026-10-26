# AI News Summarizer v2

Compares how different regions report the same news event, across languages, claim by claim, with citations.

MVP: Chinese and English; 4 regions (Australia, US, mainland China, Taiwan), 4 outlets each
(`src/news_summarizer/sources.yaml`). v1 (Streamlit + LangChain, 2025) is kept at tag `v1`.

## Status

- [x] P0 ingestion and storage: RSS / listing parsers for 16 sources, full-text extraction, Postgres
- [ ] P1 multilingual embeddings and event clustering
- [ ] P2 claim extraction, cross-language alignment, cited comparison report
- [ ] P3 FastAPI, Next.js frontend, follow-up agent
- [ ] P4 tracing, cost tracking, daily briefing

## Run locally

```bash
uv sync
uv run ans ingest --dry-run --limit 3          # no database; prints a per-source report
cp .env.example .env                           # then set DATABASE_URL (Neon)
uv run ans migrate                             # create tables, sync sources.yaml
uv run ans ingest                              # store new articles
uv run pytest                                  # offline tests; add `-m live` to hit real sites
```

## Ingestion notes

- RSS where it works; Xinhua and People's Daily are homepage link lists (date from the URL);
  CCTV has a JSON list endpoint.
- The crawler sends an honest user agent. Sites that block crawlers are dropped, not worked around
  (news.com.au was replaced by The Age for this reason).
- The public demo will show short excerpts and links only, never full article text.
- A scheduled GitHub Actions workflow runs ingestion every 6 hours.
