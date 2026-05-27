# Alpha-Bench Data Ingestion Framework

A premium, high-performance data ingestion framework designed to fetch, clean, and standardize historical OHLCV (Open, High, Low, Close, Volume) market data for the Indian Stock Market (NSE/BSE). Built using Python, modern dependency tooling (`uv`), and robust data fetchers integrated with custom aesthetic logging.

---

## 🏗️ Architectural Blueprint

The codebase is organized following strict domain-driven, modular packaging best practices:

```text
alpha-bench/
├── .venv/                      # Synced local Python virtual environment
├── src/                        # Core codebase package
│   ├── __init__.py             # Versioning and package metadata
│   ├── config.py               # Global constants and DataFrame schemas
│   ├── logger/                 # Native custom ANSI colored logging framework
│   │   ├── __init__.py
│   │   └── logger.py
│   └── data_fetchers/          # Resilient data fetching adapters
│       ├── __init__.py         # Consolidated package API imports
│       ├── yfinance_fetcher.py # Yahoo Finance adapter with suffix cleaning
│       └── jugaad_fetcher.py   # NSE India adapter with date and index sorting
├── tests/                      # Automated unit test suite
│   ├── __init__.py
│   └── test_data_fetchers.py   # Mock-based Pytest specifications
├── example/                    # Development scripts and usage demos
│   ├── logger_usage.py         # Custom logging demonstration
│   └── test_fetchers.py        # Integration test checking live APIs
├── pyproject.toml              # Modern PEP-621 metadata & tool declarations
└── README.md                   # Premium developer documentation
```

---

## ⚡ Getting Started

This project utilizes `uv` by Astral for fast, reliable package management.

### 1. Prerequisites
Ensure you have `uv` installed on your machine. If not, install it using:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Environment Setup
Clone the repository and synchronize the environment (including development packages):
```bash
# Sync dependencies and build virtual env
uv sync
```

---

## 📘 Quick Start Usage

Both data fetchers are interchangeable and return a standardized `pandas.DataFrame` matching exactly the central schema defined in `src/config.py`.

### Fetching with `yfinance`

```python
from datetime import datetime, timedelta
from src.logger import setup_logging, get_logger
from src.data_fetchers import fetch_yfinance_ohlcv

# 1. Setup native styled logger
setup_logging(default_level="INFO", console_output=True)
logger = get_logger(__name__)

# 2. Ingest Indian stock market data (cleaner auto-appends .NS)
start_date = datetime.now() - timedelta(days=15)
end_date = datetime.now()

try:
    df = fetch_yfinance_ohlcv(
        ticker="TCS", 
        start_date=start_date, 
        end_date=end_date
    )
    logger.info("Successfully fetched data!")
    print(df.head())
except Exception as e:
    logger.error(f"Failed to fetch data: {e}")
```

### Fetching from the NSE directly with `jugaad-data`

```python
from datetime import date
from src.logger import setup_logging, get_logger
from src.data_fetchers import fetch_jugaad_ohlcv

setup_logging(default_level="INFO")
logger = get_logger(__name__)

try:
    # also strips suffixes like .NS to fetch raw symbol "RELIANCE"
    df = fetch_jugaad_ohlcv(
        symbol="RELIANCE.NS",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 20)
    )
    logger.info("Successfully loaded data from NSE website!")
    print(df.head())
except Exception as e:
    logger.error(f"NSE Ingestion failed: {e}")
```

---

## 🛡️ Exception Hierarchy & Data Mapping

Both fetchers map underlying connection timeouts, missing pages, and invalid tickers onto a standard custom exception tree to ensure resilient downstream application pipelines.

### Standardized Schema Columns

Every returned DataFrame contains:
- **Index**: Named `Date` (a timezone-naive `DatetimeIndex` representing transaction days, sorted ascending).
- **Columns**: `["Open", "High", "Low", "Close", "Volume"]`.

### Resilient Error Mapping

| Exception | Raised When |
| :--- | :--- |
| `TickerNotFoundError` | The requested ticker does not exist, is delisted, or has no history. |
| `ConnectionError` | The internet is down, or rate-limiting/timeouts are triggered by target API. |
| `DataFetchError` | Base package exception for generic parser failures or schema issues. |

---

## 🧪 Quality Control & Testing

### 1. Running Unit Tests
A full, fast unit test suite with mock objects handles validating formatting and exception states without needing active internet connections:
```bash
# Run pytest with coverage reporter
PYTHONPATH=. uv run pytest tests/ --cov=src
```

### 2. Linting & Formatting
The codebase is validated against modern styling rules using Ruff:
```bash
# Run the linter
uv run ruff check src/

# Run the formatter
uv run ruff format src/
```
