-- Front-page snapshots: each run records every outlet's headlines in homepage order.
-- Items reference articles by URL (not id): a headline can be captured before its article
-- page is fetched, and the same article keeps its row across snapshots.

CREATE TABLE frontpage_snapshots (
    id          bigserial PRIMARY KEY,
    source_id   text NOT NULL REFERENCES sources (id),
    run_id      bigint REFERENCES ingest_runs (id),
    captured_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX frontpage_snapshots_source_captured
    ON frontpage_snapshots (source_id, captured_at DESC);

CREATE TABLE frontpage_items (
    snapshot_id bigint NOT NULL REFERENCES frontpage_snapshots (id) ON DELETE CASCADE,
    rank        int NOT NULL CHECK (rank >= 1),
    url         text NOT NULL,
    title       text NOT NULL,  -- anchor text from the homepage; the UI prefers articles.title
    PRIMARY KEY (snapshot_id, rank)
);

CREATE INDEX frontpage_items_url ON frontpage_items (url);
