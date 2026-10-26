from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

SOURCES_FILE = Path(__file__).resolve().parent.parent / "sources.yaml"


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    region: str  # AU | US | CN | TW
    language: str  # en | zh
    kind: str  # rss | xinhua | people | cctv
    feeds: tuple[str, ...]


@dataclass
class ListingItem:
    """One article link found in a feed or listing page, before full-text extraction."""

    source_id: str
    url: str
    title: str
    excerpt: str | None = None
    published_at: datetime | None = None


@dataclass
class Article:
    source_id: str
    url: str
    title: str
    excerpt: str | None
    content: str | None
    published_at: datetime | None
    language: str
    extra: dict = field(default_factory=dict)


def load_sources(path: Path = SOURCES_FILE) -> list[Source]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Source(**{**s, "feeds": tuple(s["feeds"])}) for s in raw]
