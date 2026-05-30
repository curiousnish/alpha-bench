"""
resilient news fetching adapter for the Knowivate News API.
Provides high-performance, robust fetching of Indian company news.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from src.config import BSE_SUFFIX, NSE_SUFFIX
from src.exceptions import ConnectionError, DataFetchError
from src.logger import get_logger


logger = get_logger(__name__)


def get_query_candidates(symbol: str) -> list[str]:
    """
    Cleans the stock symbol and returns a list of candidate search terms in order of preference.
    Strips exchange suffixes like '.NS' or '.BO' since news queries are company-based.

    To work around Knowivate's casing quirks (where uppercase symbols often trigger 500 errors,
    and lowercase/proper-case queries behave differently per keyword), we generate and test
    casing variations sequentially.

    Args:
        symbol: The stock symbol (e.g. 'RELIANCE.NS', 'tcs', 'INFY')

    Returns:
        List of deduplicated candidate search queries (e.g. ['Reliance', 'reliance', 'RELIANCE']).
    """
    cleaned = symbol.strip().upper()

    if cleaned.endswith(NSE_SUFFIX):
        cleaned = cleaned[: -len(NSE_SUFFIX)]
    elif cleaned.endswith(BSE_SUFFIX):
        cleaned = cleaned[: -len(BSE_SUFFIX)]

    # 1. Proper Case (e.g. 'Reliance', 'Tcs', 'Infosys') - most stable on Knowivate
    v_proper = cleaned.title()
    # 2. Lowercase (e.g. 'reliance', 'tcs', 'infosys')
    v_lower = cleaned.lower()
    # 3. Uppercase (e.g. 'RELIANCE', 'TCS', 'INFY')
    v_upper = cleaned

    # Return deduplicated candidates in order of preference
    candidates = []
    seen = set()
    for v in [v_proper, v_lower, v_upper]:
        if v not in seen:
            seen.add(v)
            candidates.append(v)

    return candidates


def fetch_knowivate_news(symbol: str, limit: int = 10) -> list[dict]:
    """
    Fetch historical and real-time news articles about a company from the Knowivate News API.

    To address server-side bugs and query-specific 500 errors on the free API, this fetcher
    dynamically evaluates multiple case variations (Proper Case, Lowercase, Uppercase) in a
    self-healing retry loop until it finds a format accepted by the server.

    Args:
        symbol: The stock ticker symbol (e.g., 'RELIANCE', 'TCS.NS', 'INFY').
        limit: The maximum number of news articles to return. Defaults to 10.

    Returns:
        A list of standardized dictionaries representing news articles:
        [
            {
                "title": str,
                "description": str,
                "url": str,
                "source": str,
                "published_at": datetime (timezone-naive)
            }
        ]

    Raises:
        ConnectionError: If a network/timeout issue or all casing formats fail.
        DataFetchError: If the response is incomplete or invalid.
    """
    candidates = get_query_candidates(symbol)
    base_url = "https://news.knowivate.com/api/news"

    data = None
    last_exception = None

    for query in candidates:
        params = urllib.parse.urlencode({"q": query})
        url = f"{base_url}?{params}"
        logger.info(f"Querying Knowivate News API with candidate '{query}': {url}")

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise DataFetchError(
                        f"Knowivate API returned non-200 status: {response.status}"
                    )
                raw_data = response.read().decode("utf-8")
                parsed = json.loads(raw_data)

                # Check API success key
                if parsed.get("success"):
                    data = parsed
                    logger.info(
                        f"Successfully fetched news for '{symbol}' using query candidate '{query}'"
                    )
                    break
                else:
                    logger.warning(
                        f"API returned success=False for candidate '{query}': {parsed.get('message')}"
                    )
                    last_exception = DataFetchError(
                        parsed.get("message", "API response indicated failure")
                    )

        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP Error {e.code} for query candidate '{query}': {e.reason}")
            last_exception = ConnectionError(
                f"HTTP Error {e.code} connecting to Knowivate News API: {e.reason}"
            )
        except urllib.error.URLError as e:
            logger.warning(f"Network error for query candidate '{query}': {e}")
            last_exception = ConnectionError(f"Failed to connect to Knowivate News API: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error for query candidate '{query}': {e}")
            last_exception = DataFetchError(f"Invalid JSON returned from Knowivate News API: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error for query candidate '{query}': {e}")
            last_exception = DataFetchError(f"Error fetching news from Knowivate: {e}")

    if data is None:
        logger.error(f"All query candidates failed for symbol '{symbol}'")
        if last_exception:
            raise last_exception
        raise DataFetchError(
            f"Failed to fetch news for symbol '{symbol}': all query candidates failed"
        )

    raw_news = data.get("news", [])
    if not isinstance(raw_news, list):
        logger.error("Invalid response format: 'news' key is not a list")
        raise DataFetchError("Knowivate API returned invalid 'news' format")

    logger.debug(f"Fetched {len(raw_news)} raw articles from Knowivate.")

    standardized_articles = []
    for item in raw_news[:limit]:
        title_raw = item.get("title")
        title = str(title_raw).strip() if title_raw is not None else ""

        desc_raw = item.get("description")
        description = str(desc_raw).strip() if desc_raw is not None else ""

        url_raw = item.get("url")
        url = str(url_raw).strip() if url_raw is not None else ""

        source_raw = item.get("source")
        if isinstance(source_raw, dict):
            source = (
                source_raw.get("name")
                or source_raw.get("title")
                or source_raw.get("id")
                or "Unknown"
            )
            source = str(source).strip()
        elif source_raw is not None:
            source = str(source_raw).strip()
        else:
            source = "Unknown"

        # Parse publication date to timezone-naive datetime
        pub_str = item.get("publishedAt") or item.get("createdAt")
        published_at = None

        if pub_str:
            try:
                # Handle standard ISO formats like 2026-05-28T12:00:00.000Z
                # Replace 'Z' suffix with '+00:00' for fromisoformat compliance
                clean_pub_str = str(pub_str).strip()
                if clean_pub_str.endswith("Z"):
                    clean_pub_str = clean_pub_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(clean_pub_str)
                # Convert to timezone naive
                published_at = dt.replace(tzinfo=None)
            except Exception as e:
                logger.debug(f"Could not parse publication date '{pub_str}': {e}")

        # Fallback to current time if no valid timestamp
        if published_at is None:
            published_at = datetime.now()

        standardized_articles.append(
            {
                "title": title,
                "description": description,
                "url": url,
                "source": source,
                "published_at": published_at,
            }
        )

    logger.info(
        f"Successfully processed {len(standardized_articles)} news articles for '{symbol}'."
    )
    return standardized_articles
