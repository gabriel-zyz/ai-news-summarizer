import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

SOURCES_FILE = Path(__file__).resolve().parent.parent / "sources.yaml"


@dataclass(frozen=True)
class FrontPage:
    """The outlet's homepage and the URL shape of its article links (matched on canonical URLs)."""

    url: str
    pattern: re.Pattern


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    region: str  # AU | US | CN | TW
    language: str  # en | zh
    kind: str  # rss | xinhua | people | cctv | udn
    feeds: tuple[str, ...]
    frontpage: FrontPage | None = None
    title_strip: re.Pattern | None = None  # site-name suffix on article page titles

    def clean_title(self, title: str) -> str:
        return self.title_strip.sub("", title).strip() if self.title_strip else title


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
    sources = []
    for s in raw:
        fp = s.pop("frontpage", None)
        feeds = tuple(s.pop("feeds"))
        frontpage = FrontPage(fp["url"], re.compile(fp["pattern"])) if fp else None
        strip = s.pop("title_strip", None)
        sources.append(
            Source(
                **s,
                feeds=feeds,
                frontpage=frontpage,
                title_strip=re.compile(strip) if strip else None,
            )
        )
    return sources
