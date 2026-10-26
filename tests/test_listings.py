from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from news_summarizer.ingest.extract import extract
from news_summarizer.ingest.listings import (
    CST,
    canonical_url,
    parse_cctv,
    parse_people,
    parse_rss,
    parse_udn,
    parse_xinhua,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_canonical_url_drops_tracking_and_fragment():
    url = "https://www.abc.net.au/news/story?utm_source=rss&id=7&ref=x#comments"
    assert canonical_url(url) == "https://www.abc.net.au/news/story?id=7"


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
