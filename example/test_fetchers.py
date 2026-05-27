import time
from datetime import datetime, timedelta

from src.data_fetchers import (
    TickerNotFoundError,
    fetch_jugaad_ohlcv,
    fetch_yfinance_ohlcv,
)
from src.logger import get_logger, setup_logging


logger = get_logger("test_fetchers")


def test_fetcher_success():
    """
    Test standard success path for both fetchers using well-known Indian tickers.
    """
    logger.info("=========================================")
    logger.info("TEST 1: Fetching valid tickers (Success cases)")
    logger.info("=========================================")

    # 7 days ago to today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)

    # We will test TCS and RELIANCE
    ticker_yf = "TCS"
    ticker_jg = "RELIANCE"

    # 1. Test yfinance_fetcher
    logger.info(f"--- Testing yfinance_fetcher for '{ticker_yf}' ---")
    try:
        df_yf = fetch_yfinance_ohlcv(ticker_yf, start_date=start_date, end_date=end_date)

        logger.debug(f"DataFrame Shape: {df_yf.shape}")
        logger.debug(f"DataFrame Columns: {list(df_yf.columns)}")
        logger.debug(f"DataFrame Index Name: '{df_yf.index.name}'")

        if not df_yf.empty:
            logger.info("Sample OHLCV Data from yfinance:")
            print(df_yf.head(3))
            print()

            # Basic validation
            assert list(df_yf.columns) == ["Open", "High", "Low", "Close", "Volume"]
            assert df_yf.index.name == "Date"
            logger.info(f"✓ yfinance_fetcher test PASSED for '{ticker_yf}'")
        else:
            logger.warning(
                f"yfinance returned empty dataframe for '{ticker_yf}' in range {start_date} to {end_date}"
            )

    except Exception as e:
        logger.error(f"✗ yfinance_fetcher failed unexpectedly: {e}", exc_info=True)
        raise e

    time.sleep(1.0)  # Grace period between requests

    # 2. Test jugaad_fetcher
    logger.info(f"--- Testing jugaad_fetcher for '{ticker_jg}' ---")
    try:
        df_jg = fetch_jugaad_ohlcv(ticker_jg, start_date=start_date, end_date=end_date)

        logger.debug(f"DataFrame Shape: {df_jg.shape}")
        logger.debug(f"DataFrame Columns: {list(df_jg.columns)}")
        logger.debug(f"DataFrame Index Name: '{df_jg.index.name}'")

        if not df_jg.empty:
            logger.info("Sample OHLCV Data from jugaad-data:")
            print(df_jg.head(3))
            print()

            # Basic validation
            assert list(df_jg.columns) == ["Open", "High", "Low", "Close", "Volume"]
            assert df_jg.index.name == "Date"
            logger.info(f"✓ jugaad_fetcher test PASSED for '{ticker_jg}'")
        else:
            logger.warning(
                f"jugaad-data returned empty dataframe for '{ticker_jg}' in range {start_date} to {end_date}"
            )

    except Exception as e:
        logger.error(f"✗ jugaad_fetcher failed unexpectedly: {e}", exc_info=True)
        raise e


def test_fetcher_failures():
    """
    Test exception handling path using an invalid ticker symbol.
    """
    logger.info("=========================================")
    logger.info("TEST 2: Fetching invalid tickers (Error handling)")
    logger.info("=========================================")

    invalid_ticker = "INVALID_STOCK_XYZ"
    start_date = datetime.now() - timedelta(days=10)
    end_date = datetime.now()

    # 1. Test yfinance_fetcher failure
    logger.info(f"--- Testing yfinance_fetcher error handling for '{invalid_ticker}' ---")
    try:
        fetch_yfinance_ohlcv(invalid_ticker, start_date=start_date, end_date=end_date)
        logger.error(
            "✗ Expected TickerNotFoundError but fetch succeeded (or returned data) for invalid ticker."
        )
    except TickerNotFoundError as e:
        logger.info(f"✓ yfinance_fetcher correctly raised TickerNotFoundError: {e}")
    except Exception as e:
        logger.error(f"✗ yfinance_fetcher raised wrong exception: {type(e).__name__} - {e}")

    time.sleep(1.0)  # Grace period

    # 2. Test jugaad_fetcher failure
    logger.info(f"--- Testing jugaad_fetcher error handling for '{invalid_ticker}' ---")
    try:
        fetch_jugaad_ohlcv(invalid_ticker, start_date=start_date, end_date=end_date)
        logger.error(
            "✗ Expected TickerNotFoundError but fetch succeeded (or returned data) for invalid ticker."
        )
    except TickerNotFoundError as e:
        logger.info(f"✓ jugaad_fetcher correctly raised TickerNotFoundError: {e}")
    except Exception as e:
        logger.error(f"✗ jugaad_fetcher raised wrong exception: {type(e).__name__} - {e}")


def main():
    # Configure custom logging framework
    setup_logging(default_level="DEBUG", log_file="logs/test_fetchers.log", console_output=True)

    logger.info("=========================================")
    logger.info("Starting Indian Stock Market Fetchers Test")
    logger.info("=========================================")

    try:
        test_fetcher_success()
        time.sleep(1.0)
        test_fetcher_failures()
        logger.info("=========================================")
        logger.info("All verification tests finished successfully!")
        logger.info("=========================================")
    except Exception as e:
        logger.critical(f"Verification pipeline failed: {e}")


if __name__ == "__main__":
    main()
