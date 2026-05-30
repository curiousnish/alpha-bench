import json
import urllib.error
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data_fetchers.knowivate_fetcher import fetch_knowivate_news, get_query_candidates
from src.exceptions import ConnectionError, DataFetchError


# =====================================================================
# 1. Test Query Candidates Generation
# =====================================================================


def test_get_query_candidates():
    """Verify that query candidates are correctly generated and ordered."""
    # TCS with NSE suffix
    assert get_query_candidates("TCS.NS") == ["Tcs", "tcs", "TCS"]

    # Reliance with BSE suffix
    assert get_query_candidates("RELIANCE.BO") == ["Reliance", "reliance", "RELIANCE"]

    # Single-letter symbol or short symbols
    assert get_query_candidates("sbi") == ["Sbi", "sbi", "SBI"]


# =====================================================================
# 2. Test Success Path and Response Formatting
# =====================================================================


@patch("urllib.request.urlopen")
def test_fetch_knowivate_news_success(mock_urlopen):
    """Test successful news fetching, limit enforcement, and date parsing."""
    # Create mock response object
    mock_response = MagicMock()
    mock_response.status = 200

    api_response = {
        "success": True,
        "message": "Fetched successfully",
        "news": [
            {
                "title": "TCS reports strong growth",
                "description": "Tata Consultancy Services has reported massive revenue gains.",
                "url": "https://news.example.com/tcs-growth",
                "source": "Financial Express",
                "publishedAt": "2026-05-28T12:00:00.000Z",
            },
            {
                "title": "TCS AI updates",
                "description": "TCS launches new agentic AI services.",
                "url": "https://news.example.com/tcs-ai",
                "source": {"name": "Economic Times"},
                "createdAt": "2026-05-28T11:30:00Z",
            },
        ],
    }

    mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Fetch news
    articles = fetch_knowivate_news("TCS", limit=2)

    # Verify limit enforcement
    assert len(articles) == 2

    # Verify standardization of fields for first article
    article = articles[0]
    assert article["title"] == "TCS reports strong growth"
    assert article["description"] == "Tata Consultancy Services has reported massive revenue gains."
    assert article["url"] == "https://news.example.com/tcs-growth"
    assert article["source"] == "Financial Express"

    # Verify timezone-naive datetime parsing
    assert isinstance(article["published_at"], datetime)
    assert article["published_at"].year == 2026
    assert article["published_at"].month == 5
    assert article["published_at"].day == 28
    assert article["published_at"].hour == 12
    assert article["published_at"].minute == 0

    # Verify standardization of fields for second article (where source was a dict)
    article_two = articles[1]
    assert article_two["title"] == "TCS AI updates"
    assert article_two["source"] == "Economic Times"
    assert isinstance(article_two["published_at"], datetime)


# =====================================================================
# 3. Test HTTP 500 Sequential Retry Logic
# =====================================================================


@patch("urllib.request.urlopen")
def test_fetch_knowivate_news_retry_fallback(mock_urlopen):
    """Test that a 500 error on the first candidate triggers a try on the next candidate."""
    # First call will raise HTTP 500 error for proper-case query (e.g. 'Reliance')
    http_error = urllib.error.HTTPError(
        url="https://news.knowivate.com/api/news?q=Reliance",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    # Second call succeeds for lowercase query (e.g. 'reliance')
    mock_success_response = MagicMock()
    mock_success_response.status = 200
    api_response = {
        "success": True,
        "news": [
            {
                "title": "Reliance stock surges",
                "description": "Reliance shares rally in late trading.",
                "url": "https://news.example.com/reliance",
                "source": "Mint",
                "publishedAt": "2026-05-28T12:00:00Z",
            }
        ],
    }
    mock_success_response.read.return_value = json.dumps(api_response).encode("utf-8")

    # Set side effect: first raise error, second return successful response
    mock_urlopen.side_effect = [
        http_error,
        MagicMock(__enter__=MagicMock(return_value=mock_success_response)),
    ]

    # Fetch news
    articles = fetch_knowivate_news("RELIANCE")

    assert len(articles) == 1
    assert articles[0]["title"] == "Reliance stock surges"
    # It tried "Reliance" (failed), then tried "reliance" (succeeded)
    assert mock_urlopen.call_count == 2


# =====================================================================
# 4. Test Connectivity and Exception Mapping
# =====================================================================


@patch("urllib.request.urlopen")
def test_fetch_knowivate_news_connection_error(mock_urlopen):
    """Test that connection and HTTP non-500 failures map to ConnectionError."""
    # HTTP Error 404
    http_error = urllib.error.HTTPError(
        url="https://news.knowivate.com/api/news?q=Tcs",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    mock_urlopen.side_effect = http_error

    with pytest.raises(ConnectionError):
        fetch_knowivate_news("TCS")

    # URL connection error
    mock_urlopen.side_effect = urllib.error.URLError("Network down")

    with pytest.raises(ConnectionError):
        fetch_knowivate_news("TCS")


@patch("urllib.request.urlopen")
def test_fetch_knowivate_news_data_fetch_error(mock_urlopen):
    """Test that API success=False or malformed JSON maps to DataFetchError."""
    # API indicates failure for all candidate queries
    mock_response = MagicMock()
    mock_response.status = 200
    api_response = {"success": False, "message": "Query too short"}
    mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with pytest.raises(DataFetchError):
        fetch_knowivate_news("TCS")

    # Malformed JSON response for all candidate queries
    mock_urlopen.side_effect = None
    mock_response_bad = MagicMock()
    mock_response_bad.status = 200
    mock_response_bad.read.return_value = b"{corrupt json..."
    mock_urlopen.return_value.__enter__.return_value = mock_response_bad

    with pytest.raises(DataFetchError):
        fetch_knowivate_news("TCS")
