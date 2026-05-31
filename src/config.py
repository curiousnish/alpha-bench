"""
Central configuration module for the Alpha-Bench project.
Contains system-wide constants, file paths, and standard data schema definitions
to ensure consistency and ease of maintenance.
"""

import os


# Project root directory detection
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Standard OHLCV Data Schema definition
# All data fetchers must map and clean their output columns to match exactly this schema.
STANDARD_OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

# Exchange Suffix Definitions for the Indian Stock Market
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

# Data Fetching Configurations
DEFAULT_INTERVAL = "1d"
DEFAULT_NSE_SERIES = "EQ"
DEFAULT_LOOKBACK_DAYS = 30

# Logging Configurations
DEFAULT_LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "pipeline.log")
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_PATTERN = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(filename)s:%(lineno)d - %(message)s"
)

# MLflow Configurations
DEFAULT_MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", f"file://{os.path.join(PROJECT_ROOT, 'mlruns')}"
)
DEFAULT_MLFLOW_EXPERIMENT = "alpha_bench_experiments"

