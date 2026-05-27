from datetime import date, datetime

import pandas as pd
from jugaad_data.nse import stock_df

from src.config import BSE_SUFFIX, DEFAULT_NSE_SERIES, NSE_SUFFIX, STANDARD_OHLCV_COLUMNS
from src.data_fetchers.yfinance_fetcher import ConnectionError, DataFetchError, TickerNotFoundError
from src.logger import get_logger


logger = get_logger(__name__)


def clean_nse_symbol(symbol: str) -> str:
    """
    Cleans and standardizes the stock symbol for NSE (National Stock Exchange).
    Strips off any exchange suffixes like '.NS' or '.BO' if provided.

    Args:
        symbol: The stock ticker symbol (e.g., 'RELIANCE.NS', 'TCS', 'INFY')

    Returns:
        A cleaned symbol string suitable for jugaad-data (e.g., 'RELIANCE').
    """
    symbol_cleaned = symbol.strip().upper()

    # Strip suffixes using central configuration constants
    if symbol_cleaned.endswith(NSE_SUFFIX):
        symbol_cleaned = symbol_cleaned[: -len(NSE_SUFFIX)]
    elif symbol_cleaned.endswith(BSE_SUFFIX):
        symbol_cleaned = symbol_cleaned[: -len(BSE_SUFFIX)]
        logger.warning(
            f"jugaad-data only supports NSE. Converted BSE symbol '{symbol}' to NSE symbol: '{symbol_cleaned}'"
        )

    return symbol_cleaned


def fetch_jugaad_ohlcv(
    symbol: str,
    start_date: str | datetime | date,
    end_date: str | datetime | date,
    series: str = DEFAULT_NSE_SERIES,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for an Indian stock ticker from NSE using jugaad-data.

    Args:
        symbol: The stock ticker symbol (e.g., 'RELIANCE', 'SBIN.NS').
        start_date: Start date for historical data (YYYY-MM-DD, datetime, or date object).
        end_date: End date for historical data (YYYY-MM-DD, datetime, or date object).
        series: The segment series. Defaults to DEFAULT_NSE_SERIES.

    Returns:
        A standardized pandas DataFrame containing OHLCV data with columns:
        ['Open', 'High', 'Low', 'Close', 'Volume'] and a DatetimeIndex named 'Date'.

    Raises:
        TickerNotFoundError: If the ticker/symbol is invalid or has no data on NSE.
        ConnectionError: If there's an issue connecting to NSE servers.
        DataFetchError: For other general errors during data fetching.
    """
    nse_symbol = clean_nse_symbol(symbol)

    # Convert dates to datetime.date objects required by jugaad-data
    def to_date_obj(d: str | datetime | date) -> date:
        if isinstance(d, date) and not isinstance(d, datetime):
            return d
        if isinstance(d, datetime):
            return d.date()
        try:
            # Assume YYYY-MM-DD format for string
            return datetime.strptime(str(d).strip(), "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"Invalid date format '{d}'. Expected YYYY-MM-DD: {e}")
            raise ValueError(f"Invalid date format '{d}'. Please use YYYY-MM-DD.") from e

    from_date = to_date_obj(start_date)
    to_date = to_date_obj(end_date)

    logger.info(
        f"Fetching data for '{nse_symbol}' from NSE via jugaad-data ({from_date} to {to_date})"
    )

    try:
        # Fetch data using jugaad-data
        df = stock_df(symbol=nse_symbol, from_date=from_date, to_date=to_date, series=series)
    except Exception as e:
        error_msg = str(e).lower()
        # jugaad-data or requests HTTP errors
        if (
            "connection" in error_msg
            or "timeout" in error_msg
            or "http" in error_msg
            or "max retries" in error_msg
        ):
            logger.error(
                f"Network / connection issue while querying NSE for symbol '{nse_symbol}': {e}"
            )
            raise ConnectionError(f"Failed to connect to NSE for symbol '{nse_symbol}': {e}") from e
        elif any(
            term in error_msg for term in ["symbol", "invalid", "404", "expecting value", "json"]
        ):
            logger.error(f"Invalid symbol or no data for '{nse_symbol}' on NSE: {e}")
            raise TickerNotFoundError(
                f"Symbol '{nse_symbol}' is invalid or does not exist on NSE: {e}"
            ) from e
        else:
            logger.error(f"Error fetching data for '{nse_symbol}' via jugaad-data: {e}")
            raise DataFetchError(f"Error fetching data for symbol '{nse_symbol}': {e}") from e

    if df is None or df.empty:
        # If no error was raised but empty DataFrame returned, return empty df with standard schema
        logger.warning(
            f"No records returned for NSE symbol '{nse_symbol}' between {from_date} and {to_date}."
        )
        return pd.DataFrame(columns=STANDARD_OHLCV_COLUMNS)

    # Standardize column names using uppercase mappings
    df.columns = [col.upper() for col in df.columns]

    # Map raw uppercase columns to standard config columns: Open, High, Low, Close, Volume
    mapping = {col.upper(): col for col in STANDARD_OHLCV_COLUMNS}

    # Verify all required columns are present
    for raw_col in mapping:
        if raw_col not in df.columns:
            logger.error(
                f"Missing expected NSE column '{raw_col}' in jugaad-data response. Columns: {list(df.columns)}"
            )
            raise DataFetchError(f"NSE returned incomplete data. Missing column: '{raw_col}'")

    # Keep only the columns we want to standardize
    df_clean = df[list(mapping.keys())].rename(columns=mapping)

    # Process the Date column
    if "DATE" not in df.columns:
        logger.error("Missing expected 'DATE' column in jugaad-data response.")
        raise DataFetchError("NSE returned data without a DATE column.")

    # Convert 'DATE' to datetime series, set it as index, name it 'Date'
    try:
        dates = pd.to_datetime(df["DATE"])
        df_clean.index = dates
        df_clean.index.name = "Date"
    except Exception as e:
        logger.error(f"Failed to parse dates from NSE response: {e}")
        raise DataFetchError(f"Error parsing date column: {e}") from e

    # Sort the index in ascending order (jugaad-data sometimes returns descending order)
    df_clean = df_clean.sort_index()

    logger.info(f"Successfully fetched {len(df_clean)} records for '{nse_symbol}' via jugaad-data.")
    return df_clean
