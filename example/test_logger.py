import time

from src.logger import get_logger, setup_logging


# Get a logger for the current entrypoint module
logger = get_logger(__name__)


def simulate_stock_prediction_pipeline():
    """
    Simulates a standard machine learning stock prediction pipeline
    to showcase different log severity levels and aesthetic terminal styling.
    """
    logger.info("Initializing stock prediction pipeline...")

    # Simulate step 1: Data ingestion
    logger.info("Step 1/4: Ingesting market ticker data...")
    time.sleep(0.2)
    logger.debug("Fetched 15,000 historical price records for AAPL, MSFT, GOOGL")

    # Simulate step 2: Feature engineering
    logger.info("Step 2/4: Performing feature engineering...")
    time.sleep(0.2)
    logger.debug("Computed 14-day RSI and 50-day moving average metrics")

    # Simulate a potential non-blocking warning (step 3)
    logger.warning(
        "Feature 'VolumeVolatility' has 3.5%% missing values. Imputing with column median."
    )

    # Simulate step 4: Model evaluation / prediction
    logger.info("Step 3/4: Loading prediction models and running backtest...")
    time.sleep(0.3)
    logger.debug("Model accuracy score: 0.72. F1-score: 0.70.")

    # Simulate a failure
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
    # Setup logging globally
    # Directs console logs to stdout and saves file logs to logs/pipeline.log
    setup_logging(default_level="DEBUG", log_file="logs/pipeline.log", console_output=True)

    logger.info("=========================================")
    logger.info("Alpha-Bench Machine Learning Workspace Started")
    logger.info("=========================================")

    simulate_stock_prediction_pipeline()

    logger.info("Pipeline demonstration finished.")


if __name__ == "__main__":
    main()
