import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# An honest user agent: if a site blocks it, we drop the site rather than disguise the crawler.
USER_AGENT = "ai-news-summarizer/0.2 (+https://github.com/gabriel-zyz/ai-news-summarizer)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en,zh;q=0.9"},
        timeout=TIMEOUT,
        follow_redirects=True,
    )


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.TransportError)


@retry(
    retry=retry_if_exception(_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
def get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url)
    resp.raise_for_status()
    return resp
