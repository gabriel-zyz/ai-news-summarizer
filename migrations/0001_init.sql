-- P0: sources, articles, ingest runs. Embeddings (pgvector) arrive with P1.

CREATE TABLE sources (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    region      text NOT NULL CHECK (region IN ('AU', 'US', 'CN', 'TW')),
    language    text NOT NULL CHECK (language IN ('en', 'zh')),
    kind        text NOT NULL,
    feeds       text[] NOT NULL,
    active      boolean NOT NULL DEFAULT true
);

CREATE TABLE ingest_runs (
    id          bigserial PRIMARY KEY,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status      text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    stats       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE articles (
    id              bigserial PRIMARY KEY,
    source_id       text NOT NULL REFERENCES sources (id),
    url             text NOT NULL UNIQUE,
    title           text NOT NULL,
    excerpt         text,
    content         text,
    content_hash    text,
    language        text NOT NULL,
    published_at    timestamptz,
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    extraction      text NOT NULL CHECK (extraction IN ('ok', 'empty', 'error')),
    run_id          bigint REFERENCES ingest_runs (id)
);

CREATE INDEX articles_source_published ON articles (source_id, published_at DESC);
CREATE INDEX articles_published ON articles (published_at DESC);
-- Same text republished under another URL (wire copy, syndication).
CREATE INDEX articles_content_hash ON articles (content_hash);
