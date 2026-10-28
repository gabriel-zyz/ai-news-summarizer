import argparse
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from .ingest import pipeline
from .ingest.models import load_sources


def cmd_migrate(args) -> None:
    from . import db

    with db.connect() as conn:
        applied = db.migrate(conn)
        db.sync_sources(conn, load_sources())
    print(f"applied: {applied or 'nothing new'}; sources synced")


def cmd_ingest(args) -> None:
    sources = load_sources()
    if args.source:
        sources = [s for s in sources if s.id in args.source]
        if not sources:
            sys.exit(f"no source matches {args.source}")
    opts = {"max_per_source": args.limit, "max_age": timedelta(hours=args.max_age_hours)}

    if args.dry_run:
        results = pipeline.run(sources, **opts)
        if args.out:
            with Path(args.out).open("w", encoding="utf-8") as f:
                for r in results:
                    for a in r.articles:
                        row = {**a.__dict__, "published_at": a.published_at and
                               a.published_at.isoformat()}
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        _report(results)
        return

    from . import db

    with db.connect() as conn:
        run_id = db.start_run(conn)
        try:
            results = pipeline.run(sources, is_known=lambda urls: db.known_urls(conn, urls), **opts)
            inserted = sum(db.insert_articles(conn, r.articles, run_id) for r in results)
            for r in results:
                db.insert_frontpage(conn, run_id, r.source_id, r.frontpage)
        except Exception as exc:
            db.finish_run(conn, run_id, "failed", {"error": repr(exc)})
            raise
        failed = [r.source_id for r in results if not r.ok]
        status = "ok" if not failed else ("failed" if len(failed) == len(results) else "partial")
        db.finish_run(conn, run_id, status, {
            "inserted": inserted,
            "failed_sources": failed,
            "sources": {r.source_id: r.stats() for r in results},
        })
    _report(results)
    print(f"run {run_id}: {status}, inserted {inserted}")
    if status == "failed":
        sys.exit(1)


def _report(results) -> None:
    print(f"{'source':<12} {'front':>5} {'listed':>6} {'new':>4} {'text':>4}  errors")
    for r in results:
        s = r.stats()
        print(f"{r.source_id:<12} {s['frontpage']:>5} {s['listed']:>6} {s['new']:>4} "
              f"{s['extracted']:>4}  "
              f"{len(r.errors)}{'  ' + r.errors[0][:80] if r.errors else ''}")


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="ans")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("migrate", help="apply SQL migrations and sync sources.yaml")
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser("ingest", help="fetch new articles from all sources")
    p.add_argument("--source", nargs="*", help="only these source ids")
    p.add_argument("--limit", type=int, default=40, help="max new articles per source")
    p.add_argument("--max-age-hours", type=int, default=48)
    p.add_argument("--dry-run", action="store_true", help="no database; print a report")
    p.add_argument("--out", help="with --dry-run: write articles as JSONL")
    p.set_defaults(func=cmd_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
