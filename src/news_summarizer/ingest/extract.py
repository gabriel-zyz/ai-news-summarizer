import re
from collections.abc import Callable
from datetime import datetime, tzinfo

import lxml.html
import trafilatura


def extract(html: bytes, url: str, tz: tzinfo) -> tuple[str | None, datetime | None, str | None]:
    """Return (full text, published date from page metadata, page title).

    `tz` is the outlet's local zone, used when the page gives a bare date.
    """
    doc = trafilatura.bare_extraction(
        html,
        url=url,
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    site = next((f for host, f in SITE_BODY.items() if f"//{host}/" in url), None)
    text = (site and site(html)) or (doc.text.strip() if doc and doc.text else None)
    published = None
    if doc and doc.date:
        try:
            published = datetime.fromisoformat(doc.date)
        except ValueError:
            published = None
    if published and published.tzinfo is None:
        published = published.replace(tzinfo=tz)
    return text or None, published, doc.title if doc else None


def _paragraphs(fragment: str) -> str | None:
    root = lxml.html.fromstring(f"<div>{fragment}</div>")
    paras = [" ".join(p.text_content().split()) for p in root.iter("p")]
    return "\n".join(p for p in paras if p) or None


_CCTV_BODY = re.compile(rb"var\s+contentdate\s*=\s*'(.*?)'\s*</script>", re.DOTALL)
_CCTV_VIDEO = re.compile(r"\[!--begin:htmlVideoCode--\].*?\[!--end:htmlVideoCode--\]", re.DOTALL)


def _cctv(html: bytes) -> str | None:
    """CCTV renders the body from a JS string (`var contentdate = '<p>...'`) into an empty div."""
    m = _CCTV_BODY.search(html)
    if not m:
        return None
    return _paragraphs(_CCTV_VIDEO.sub("", m[1].decode("utf-8", "replace")))


def _xpath(path: str) -> Callable[[bytes], str | None]:
    def body(html: bytes) -> str | None:
        nodes = lxml.html.fromstring(html).xpath(path)
        return _paragraphs(lxml.html.tostring(nodes[0], encoding="unicode")) if nodes else None

    return body


# Sites where trafilatura misses the body; their extractor runs first.
SITE_BODY: dict[str, Callable[[bytes], str | None]] = {
    "news.cctv.com": _cctv,
    # trafilatura sometimes returns only the audio player label (聽新聞).
    "udn.com": _xpath("//section[contains(@class, 'article-content__editor')]"),
}
