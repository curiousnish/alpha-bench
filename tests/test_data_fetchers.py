from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import STANDARD_OHLCV_COLUMNS
from src.data_fetchers.jugaad_fetcher import clean_nse_symbol, fetch_jugaad_ohlcv
from src.data_fetchers.yfinance_fetcher import (
    ConnectionError,
    TickerNotFoundError,
    clean_indian_ticker,
    fetch_yfinance_ohlcv,
)


# =====================================================================
# 1. Test Ticker / Symbol Cleaning Utilities
# =====================================================================


def test_clean_indian_ticker():
    """Verify that yfinance ticker cleaning appends proper NSE/BSE suffixes."""
    # Test defaulting to NSE (.NS)
    assert clean_indian_ticker("RELIANCE") == "RELIANCE.NS"
    assert clean_indian_ticker("tcs") == "TCS.NS"

    # Test preserving explicit exchange suffixes
    assert clean_indian_ticker("INFY.NS") == "INFY.NS"
    assert clean_indian_ticker("500325.BO") == "500325.BO"

    # Test handling of whitespaces
    assert clean_indian_ticker("  sbin  ") == "SBIN.NS"


def test_clean_nse_symbol():
    """Verify that jugaad-data cleaning correctly strips suffixes for NSE."""
    # Test stripping NSE suffix
    assert clean_nse_symbol("RELIANCE.NS") == "RELIANCE"

    # Test stripping BSE suffix (which triggers warning)
    assert clean_nse_symbol("TCS.BO") == "TCS"

    # Test keeping standard raw symbols
    assert clean_nse_symbol("INFY") == "INFY"
    assert clean_nse_symbol("  sbin  ") == "SBIN"


# =====================================================================
# 2. Test Yahoo Finance Fetcher (Mocked)
# =====================================================================


@patch("yfinance.Ticker")
def test_fetch_yfinance_ohlcv_success(mock_ticker):
    """Test successful data fetching and schema mapping in yfinance fetcher."""
    # Create a mock historical dataframe returned by yfinance
    mock_df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 100.0],
            "Close": [104.0, 105.0],
            "Volume": [1000, 1100],
            "Dividends": [0.0, 0.0],
            "Stock Splits": [0, 0],
        },
        index=pd.to_datetime(["2026-05-18", "2026-05-19"]),
    )
    mock_df.index.name = "Date"

    # Setup mock ticker instance behaviour
    mock_instance = MagicMock()
    mock_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_instance

    # Run fetcher
    df = fetch_yfinance_ohlcv("RELIANCE", "2026-05-18", "2026-05-19")

    # Assertions
    assert not df.empty
    assert list(df.columns) == STANDARD_OHLCV_COLUMNS
    assert df.index.name == "Date"
    assert df.iloc[0]["Open"] == 100.0
    assert df.iloc[1]["Volume"] == 1100
    assert "Dividends" not in df.columns  # Unnecessary columns should be stripped

    # Verify mock was called correctly
    mock_ticker.assert_called_once_with("RELIANCE.NS")
    mock_instance.history.assert_called_once_with(
        start="2026-05-18", end="2026-05-19", interval="1d"
    )


@patch("yfinance.Ticker")
def test_fetch_yfinance_ticker_not_found(mock_ticker):
    """Test that TickerNotFoundError is correctly raised for invalid symbols."""
    # Setup mock ticker to return empty dataframe and trigger check
    mock_instance = MagicMock()
    mock_instance.history.return_value = pd.DataFrame()
    mock_instance.info = {}  # Empty dict represents invalid ticker in yfinance
    mock_ticker.return_value = mock_instance

    with pytest.raises(TickerNotFoundError):
        fetch_yfinance_ohlcv("INVALID", "2026-05-18", "2026-05-19")


@patch("yfinance.Ticker")
def test_fetch_yfinance_connection_error(mock_ticker):
    """Test connection exception translation in yfinance fetcher."""
    mock_instance = MagicMock()
    mock_instance.history.side_effect = Exception("HTTP Connection Timeout")
    mock_ticker.return_value = mock_instance

    with pytest.raises(ConnectionError):
        fetch_yfinance_ohlcv("RELIANCE", "2026-05-18", "2026-05-19")


# =====================================================================
# 3. Test Jugaad Data Fetcher (Mocked)
# =====================================================================


@patch("src.data_fetchers.jugaad_fetcher.stock_df")
def test_fetch_jugaad_ohlcv_success(mock_stock_df):
    """Test successful data fetching and schema mapping in jugaad-data fetcher."""
    # Create mock dataframe returned by jugaad-data
    mock_df = pd.DataFrame(
        {
            "DATE": [
                date(2026, 5, 19),
                date(2026, 5, 18),
            ],  # Intentionally out of order to test sorting
            "SERIES": ["EQ", "EQ"],
            "OPEN": [101.0, 100.0],
            "HIGH": [106.0, 105.0],
            "LOW": [100.0, 99.0],
            "PREV. CLOSE": [100.0, 99.0],
            "LTP": [105.0, 104.0],
            "CLOSE": [105.0, 104.0],
            "VWAP": [103.0, 102.0],
            "VOLUME": [1100, 1000],
        }
    )

    mock_stock_df.return_value = mock_df

    # Run fetcher
    df = fetch_jugaad_ohlcv("RELIANCE.NS", "2026-05-18", "2026-05-19")

    # Assertions
    assert not df.empty
    assert list(df.columns) == STANDARD_OHLCV_COLUMNS
    assert df.index.name == "Date"

    # Assert sorting is correct (2026-05-18 should come first)
    assert df.index[0] == pd.Timestamp("2026-05-18")
    assert df.iloc[0]["Open"] == 100.0
    assert df.iloc[1]["Volume"] == 1100
    assert "VWAP" not in df.columns

    # Verify mock calls
    mock_stock_df.assert_called_once_with(
        symbol="RELIANCE", from_date=date(2026, 5, 18), to_date=date(2026, 5, 19), series="EQ"
    )


@patch("src.data_fetchers.jugaad_fetcher.stock_df")
def test_fetch_jugaad_ticker_not_found(mock_stock_df):
    """Test that TickerNotFoundError is correctly raised for invalid symbols in jugaad-data."""
    mock_stock_df.side_effect = Exception("Expecting value: line 1 column 1 (char 0)")

    with pytest.raises(TickerNotFoundError):
        fetch_jugaad_ohlcv("INVALID", "2026-05-18", "2026-05-19")


@patch("src.data_fetchers.jugaad_fetcher.stock_df")
def test_fetch_jugaad_connection_error(mock_stock_df):
    """Test connection exception translation in jugaad-data fetcher."""
    mock_stock_df.side_effect = Exception("urllib3 Connection Refused")

    with pytest.raises(ConnectionError):
        fetch_jugaad_ohlcv("RELIANCE", "2026-05-18", "2026-05-19")
