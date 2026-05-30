"""
demo_news_fetcher.py — Live integration smoke-test and developer demo for the Knowivate News Fetcher.

Queries and standardizes news about TCS, Reliance, and Infosys from the
Knowivate API to verify live network connectivity and normalization logic.

Usage:
    uv run python scripts/demo_news_fetcher.py
"""

import time

from src.data_fetchers import fetch_knowivate_news
from src.logger import get_logger, setup_logging


logger = get_logger(__name__)


def run_news_demo():
    """Run a live news fetching smoke test for multiple stocks."""
    setup_logging(default_level="INFO", console_output=True)

    logger.info("====================================================")
    logger.info("Starting Knowivate News Ingestion Smoke Test")
    logger.info("====================================================")

    test_tickers = ["TCS.NS", "RELIANCE.NS", "INFY"]

    for ticker in test_tickers:
        logger.info(f"\n--- Ingesting news for ticker: '{ticker}' ---")
        try:
            articles = fetch_knowivate_news(ticker, limit=3)
            logger.info(f"Successfully retrieved {len(articles)} articles!")

            for i, article in enumerate(articles, start=1):
                print(f"\n[Article {i}]")
                print(f"Title:        {article['title']}")
                print(f"Source:       {article['source']}")
                print(f"Published At: {article['published_at']}")
                print(f"URL:          {article['url']}")
                print(f"Description:  {article['description'][:120]}...")
            print("-" * 50)
        except Exception as e:
            logger.error(f"Failed to fetch news for '{ticker}': {e}", exc_info=True)

        time.sleep(1.0)  # Rate limiting safety cushion

    logger.info("\n====================================================")
    logger.info("Smoke test pipeline completed.")
    logger.info("====================================================")


if __name__ == "__main__":
    run_news_demo()
