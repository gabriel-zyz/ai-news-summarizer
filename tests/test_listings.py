import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from news_summarizer.ingest.extract import extract
from news_summarizer.ingest.listings import (
    CST,
    _headline,
    canonical_url,
    parse_cctv,
    parse_frontpage,
    parse_people,
    parse_rss,
    parse_udn,
    parse_xinhua,
    url_date,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_canonical_url_drops_tracking_and_fragment():
    url = "https://www.abc.net.au/news/story?utm_source=rss&id=7&ref=x#comments"
    assert canonical_url(url) == "https://www.abc.net.au/news/story?id=7"


def test_canonical_url_repairs_doubled_host():
    url = "https://www.chinanews.com.cnhttps://www.chinanews.com.cn/tp/hd2011/2026/10-28/1.shtml"
    assert canonical_url(url) == "https://www.chinanews.com.cn/tp/hd2011/2026/10-28/1.shtml"


def test_rss_treats_1970_dates_as_unknown():
    body = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>A</title><link>https://x.test/a?utm_medium=rss</link>
        <pubDate>Thu, 01 Jan 1970 08:00:00 +0800</pubDate></item>
      <item><title><![CDATA[<b>B</b>]]></title><link>https://x.test/b</link>
        <description>&lt;p&gt;Hello  world&lt;/p&gt;</description>
        <pubDate>Mon, 26 Oct 2026 07:11:24 GMT</pubDate></item>
      <item><title>no link</title></item>
    </channel></rss>"""
    a, b = parse_rss("s", body, "https://x.test/feed")
    assert (a.url, a.published_at) == ("https://x.test/a", None)
    assert b.title == "B" and b.excerpt == "Hello world"
    assert b.published_at == datetime(2026, 10, 26, 7, 11, 24, tzinfo=UTC)


HOMEPAGE = """<html><body>
  <a href="/politics/20261026/e4e83e0e18924ffdb2f0788e7a0ee27e/c.html"><img src="x.jpg"></a>
  <a href="https://www.news.cn/politics/20261026/e4e83e0e18924ffdb2f0788e7a0ee27e/c.html">
     作风建设永远在路上</a>
  <a href="https://www.news.cn/photo/20261026/decf7e8ec670439f886c44c5bc411f48/c.html">图片新闻标题</a>
  <a href="https://www.news.cn/2023homepro/css/x.css">css</a>
  <a href="http://politics.people.com.cn/n1/2026/1026/c1024-40806006.html">人民网要闻标题</a>
  <a href="http://pic.people.com.cn/n1/2026/1026/c426981-40805699.html">图片频道标题</a>
</body></html>""".encode()


def test_xinhua_keeps_article_links_with_text_and_url_date():
    items = parse_xinhua("xinhua", HOMEPAGE, "https://www.news.cn/")
    assert [i.title for i in items] == ["作风建设永远在路上"]
    assert items[0].published_at == datetime(2026, 10, 26, tzinfo=CST)


def test_people_skips_photo_channel():
    items = parse_people("people", HOMEPAGE, "http://www.people.com.cn/")
    assert [i.url for i in items] == [
        "http://politics.people.com.cn/n1/2026/1026/c1024-40806006.html"
    ]


def test_cctv_jsonp():
    items = parse_cctv("cctv", (FIXTURES / "cctv_news_1.jsonp").read_bytes(), "")
    assert len(items) > 50
    first = items[0]
    assert first.url.startswith("https://news.cctv.com/2026/10/26/")
    assert first.published_at == datetime(2026, 10, 26, 15, 32, 39, tzinfo=CST)
    assert first.excerpt


def test_udn_json_uses_local_time_and_skips_paywalled():
    items = parse_udn("udn", (FIXTURES / "udn_breaknews.json").read_bytes(), "https://udn.com/api/more")
    assert items and all(i.url.startswith("https://udn.com/news/story/") for i in items)
    assert all("?" not in i.url for i in items)
    # dateTime says 15:33:24Z but means Taipei time; we read the plain date field.
    assert items[0].published_at.utcoffset().total_seconds() == 8 * 3600


def test_cctv_body_comes_from_js_string():
    html = (FIXTURES / "cctv_article.html").read_bytes()
    text, _, _ = extract(html, "https://news.cctv.com/2026/10/26/ARTIk9vk4llHis2NeHKjUPgf261026.shtml",
                         ZoneInfo("Asia/Shanghai"))
    assert text.startswith("央视网消息：10月26日，国家能源局发布1—9月份全国电力统计数据。")


FRONT = b"""<html><body>
  <a href="https://news.test/2026/10/28/lead-story">2 comments</a>
  <a href="https://news.test/2026/10/28/lead-story"><img src="x.jpg"></a>
  <a href="https://news.test/2026/10/28/lead-story?utm_source=home">Lead story headline</a>
  <a href="https://news.test/2026/09/04/pinned-special">Pinned special from September</a>
  <a href="https://news.test/about">About us</a>
  <a href="https://news.test/2026/10/28/second">14:17 Second story</a>
  <a href="https://news.test/2026/10/28/third">Third story 14:08 teaser text</a>
  <a href="https://news.test/2026/10/28/lead-story">Lead story headline with a longer teaser</a>
</body></html>"""


def test_frontpage_keeps_homepage_order_and_drops_stale_links():
    now = datetime(2026, 10, 28, 12, tzinfo=UTC)
    items = parse_frontpage(
        "s", FRONT, "https://news.test/", re.compile(r"^https://news\.test/\d{4}/"), now=now
    )
    assert [(i.url.rsplit("/", 1)[1], i.title) for i in items] == [
        ("lead-story", "Lead story headline"),
        ("second", "Second story"),
        ("third", "Third story"),
    ]
    assert parse_frontpage("s", FRONT, "https://news.test/", re.compile("^https://"), limit=1,
                           now=now)[0].title == "Lead story headline"


@pytest.mark.parametrize(
    ("url", "day"),
    [
        ("https://www.abc.net.au/news/2026-10-28/inflation/107317382", 28),
        ("https://www.theguardian.com/world/2026/oct/27/israel-election", 27),
        ("https://www.smh.com.au/politics/nsw/a-fantasy-20261026-p61abc.html", 26),
        ("http://politics.people.com.cn/n1/2026/1025/c1024-40806006.html", 25),
        ("https://www.chinanews.com.cn/gn/2026/10-24/10721559.shtml", 24),
        ("https://www.cna.com.tw/news/aipl/202610230137.aspx", 23),
        ("https://7news.com.au/news/missing-grandmother-c-20871234", None),
    ],
)
def test_url_date(url, day):
    assert (url_date(url).day if url_date(url) else None) == day


def test_headline_strips_section_and_time_prefix():
    assert _headline("政治13:44參選人身分證字號全都露？") == "參選人身分證字號全都露？"
