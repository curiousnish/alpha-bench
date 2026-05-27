"""
demo_logger.py — Developer demo script for the Alpha-Bench custom logger.

Demonstrates all severity levels (DEBUG → CRITICAL) and ANSI colour output
of the ColouredFormatter by simulating a mock ML pipeline run.

Usage:
    uv run python scripts/demo_logger.py
"""

import time

from src.logger import get_logger, setup_logging


logger = get_logger(__name__)


def simulate_stock_prediction_pipeline():
    """
    Simulates a standard ML stock prediction pipeline run to showcase
    all log severity levels and ANSI terminal styling.
    """
    logger.info("Initializing stock prediction pipeline...")

    # Step 1: Data ingestion
    logger.info("Step 1/4: Ingesting market ticker data...")
    time.sleep(0.2)
    logger.debug("Fetched 15,000 historical price records for AAPL, MSFT, GOOGL")

    # Step 2: Feature engineering
    logger.info("Step 2/4: Performing feature engineering...")
    time.sleep(0.2)
    logger.debug("Computed 14-day RSI and 50-day moving average metrics")

    # Step 3: Non-blocking data quality warning
    logger.warning(
        "Feature 'VolumeVolatility' has 3.5%% missing values. Imputing with column median."
    )

    # Step 4: Model evaluation
    logger.info("Step 3/4: Loading prediction models and running backtest...")
    time.sleep(0.3)
    logger.debug("Model accuracy score: 0.72. F1-score: 0.70.")

    # Simulate a backend connectivity failure
    try:
        logger.info("Step 4/4: Exporting evaluation metrics to FastAPI backend...")
        time.sleep(0.1)
        raise ConnectionRefusedError(
            "FastAPI server at http://localhost:8000/api/v1/metrics is unreachable."
        )
    except Exception as e:
        logger.error(f"Failed to post evaluation metrics to backend: {e}", exc_info=True)
        logger.critical(
            "Pipeline execution completed with CRITICAL errors. Aborting downstream deployment."
        )


def main():
    setup_logging(default_level="DEBUG", console_output=True)

    logger.info("=========================================")
    logger.info("Alpha-Bench Logger Demo Started")
    logger.info("=========================================")

    simulate_stock_prediction_pipeline()

    logger.info("Demo finished.")


if __name__ == "__main__":
    main()
