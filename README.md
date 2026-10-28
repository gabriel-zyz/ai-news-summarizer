# AI News Summarizer v2

Compares how different regions report the same news event, across languages, claim by claim, with citations.

MVP: Chinese and English; 4 regions (Australia, US, mainland China, Taiwan), 4 outlets each
(`src/news_summarizer/sources.yaml`). v1 (Streamlit + LangChain, 2025) is kept at tag `v1`.

## What it does

1. **Front pages:** what each outlet leads with right now, in its own homepage order
   (`web/`, live on Vercel).
2. **How others report it** *(next)*: Chinese- and English-language reports of the same event
   clustered and compared claim by claim, with citations.
3. **Daily briefing** *(later)*.

## Status

- [x] P0 ingestion and storage: RSS / listing parsers for 16 sources, full-text extraction, Postgres
- [x] Front pages: homepage headline order captured every run; FastAPI + Next.js home page
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

Web app (from `web/`):

```bash
npm install
uv run --project .. uvicorn api.index:app --port 8000 --reload --env-file ../.env   # API
npm run dev                                                                           # http://localhost:3000
```

## Layout and deployment

- `src/news_summarizer/` — ingestion pipeline (Python), run every 6 hours by GitHub Actions.
- `web/` — Vercel project (root directory `web`): Next.js front end plus a read-only FastAPI
  function in `web/api/index.py`. Functions run in Sydney (`syd1`), next to the Neon database.
- Postgres on Neon (Sydney). Ingestion uses the direct connection; Vercel uses the pooled one.

## Ingestion notes

- RSS where it works; Xinhua and People's Daily are homepage link lists (date from the URL);
  CCTV has a JSON list endpoint.
- Front pages: each outlet's homepage is read in DOM order, filtered by a per-outlet article-URL
  pattern (`sources.yaml`), stale pinned links dropped, top 10 stored per snapshot.
- The crawler sends an honest user agent. Sites that block crawlers are dropped, not worked around
  (news.com.au was replaced by 7News for this reason).
- The public demo will show short excerpts and links only, never full article text.
- A scheduled GitHub Actions workflow runs ingestion every 6 hours.
