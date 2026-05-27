from datetime import datetime

import pandas as pd
import yfinance as yf

from src.config import BSE_SUFFIX, DEFAULT_INTERVAL, NSE_SUFFIX, STANDARD_OHLCV_COLUMNS
from src.exceptions import ConnectionError, DataFetchError, TickerNotFoundError
from src.logger import get_logger


logger = get_logger(__name__)


def clean_indian_ticker(ticker: str) -> str:
    """
    Standardize the stock ticker for the Indian market.
    If no suffix (.NS or .BO) is provided, defaults to National Stock Exchange (.NS).

    Args:
        ticker: The stock symbol (e.g., 'RELIANCE', 'TCS.NS', '500325.BO')

    Returns:
        Standardized ticker string compatible with yfinance.
    """
    ticker_cleaned = ticker.strip().upper()

    if not (ticker_cleaned.endswith(NSE_SUFFIX) or ticker_cleaned.endswith(BSE_SUFFIX)):
        # Default to National Stock Exchange (.NS)
        ticker_cleaned = f"{ticker_cleaned}{NSE_SUFFIX}"
        logger.debug(
            f"No exchange suffix specified for '{ticker}'. Defaulting to NSE: '{ticker_cleaned}'"
        )

    return ticker_cleaned


def fetch_yfinance_ohlcv(
    ticker: str,
    start_date: str | datetime,
    end_date: str | datetime,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for an Indian stock ticker from Yahoo Finance.

    Args:
        ticker: The stock ticker symbol (e.g., 'RELIANCE', 'INFY.NS').
        start_date: Start date for historical data (YYYY-MM-DD or datetime object).
        end_date: End date for historical data (YYYY-MM-DD or datetime object).
        interval: Data interval (e.g., '1d', '1wk', '1mo'). Defaults to DEFAULT_INTERVAL.

    Returns:
        A standardized pandas DataFrame containing OHLCV data with columns:
        ['Open', 'High', 'Low', 'Close', 'Volume'] and a DatetimeIndex named 'Date'.

    Raises:
        TickerNotFoundError: If the ticker is invalid or no data is returned.
        ConnectionError: If there's an issue connecting to Yahoo Finance.
        DataFetchError: For other general errors during data fetching.
    """
    standard_ticker = clean_indian_ticker(ticker)

    # Format dates to string YYYY-MM-DD if they are datetime objects
    start_str = (
        start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else str(start_date)
    )
    end_str = end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else str(end_date)

    logger.info(
        f"Fetching data for '{standard_ticker}' from Yahoo Finance ({start_str} to {end_str})"
    )

    try:
        # Create Ticker object to check info or history
        ticker_obj = yf.Ticker(standard_ticker)

        # Download historical data
        df = ticker_obj.history(start=start_str, end=end_str, interval=interval)

    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "timeout" in error_msg or "http" in error_msg:
            logger.error(f"Network issue encountered while fetching '{standard_ticker}': {e}")
            raise ConnectionError(
                f"Failed to connect to Yahoo Finance for ticker '{standard_ticker}': {e}"
            ) from e
        else:
            logger.error(
                f"Error fetching data for ticker '{standard_ticker}' from Yahoo Finance: {e}"
            )
            raise DataFetchError(f"Error fetching data for ticker '{standard_ticker}': {e}") from e

    # Check if empty dataframe is returned
    if df.empty:
        logger.warning(
            f"No historical data returned for ticker '{standard_ticker}' between {start_str} and {end_str}."
        )
        # Let's perform a check to see if the ticker actually exists by trying to access info
        try:
            # yfinance's info dict will be empty or raise error for completely invalid tickers
            if not ticker_obj.info or "symbol" not in ticker_obj.info:
                raise TickerNotFoundError(
                    f"Ticker '{standard_ticker}' is invalid or does not exist on Yahoo Finance."
                )
        except Exception:
            raise TickerNotFoundError(
                f"Ticker '{standard_ticker}' is invalid or has no data available on Yahoo Finance."
            ) from None

        # If ticker exists but simply has no data in this date range
        return pd.DataFrame(columns=STANDARD_OHLCV_COLUMNS)

    # Standardize columns to standard OHLCV
    # yfinance history returns: ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
    for col in STANDARD_OHLCV_COLUMNS:
        if col not in df.columns:
            logger.error(f"Missing expected OHLCV column '{col}' in yfinance response.")
            raise DataFetchError(
                f"Yahoo Finance returned incomplete OHLCV data for '{standard_ticker}'. Missing column: {col}"
            )

    # Filter only expected columns
    df_clean = df[STANDARD_OHLCV_COLUMNS].copy()

    # Make index timezone naive (standard for project usability) and ensure name is 'Date'
    if df_clean.index.tz is not None:
        df_clean.index = df_clean.index.tz_localize(None)
    df_clean.index.name = "Date"

    logger.info(f"Successfully fetched {len(df_clean)} records for '{standard_ticker}'.")
    return df_clean
