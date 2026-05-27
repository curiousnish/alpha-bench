# Alpha-Bench Data Ingestion Framework

A high-performance data ingestion framework for fetching, cleaning, and standardizing historical OHLCV (Open, High, Low, Close, Volume) market data for the Indian Stock Market (NSE/BSE). Built with Python, `uv` for dependency management, and a custom ANSI-coloured logging framework.

---

## 🏗️ Project Structure

```text
alpha-bench/
├── src/                        # Core library package
│   ├── __init__.py             # Package version and metadata
│   ├── config.py               # Global constants and DataFrame schema
│   ├── exceptions.py           # Shared exception hierarchy (DataFetchError, etc.)
│   ├── logger/                 # Custom ANSI-coloured logging framework
│   │   ├── __init__.py         # Public API: setup_logging, get_logger
│   │   └── _core.py            # Internal logger implementation
│   └── data_fetchers/          # Resilient data fetching adapters
│       ├── __init__.py         # Consolidated public API exports
│       ├── yfinance_fetcher.py # Yahoo Finance adapter (auto-appends .NS suffix)
│       └── jugaad_fetcher.py   # NSE India adapter via jugaad-data
├── tests/                      # Automated unit test suite (offline, mocked)
│   ├── __init__.py
│   └── test_data_fetchers.py   # Mock-based Pytest specifications
├── scripts/                    # Developer utility scripts (not part of library API)
│   ├── demo_logger.py          # ANSI logger output demonstration
│   └── run_fetchers.py         # Live integration smoke-test (requires internet)
├── pyproject.toml              # PEP-621 project metadata and tool configuration
├── .pre-commit-config.yaml     # Pre-commit hooks (ruff lint + format)
└── README.md
```

---

## ⚡ Getting Started

This project uses [`uv`](https://github.com/astral-sh/uv) for fast, reliable dependency management.

### 1. Prerequisites

Install `uv` if not already available:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Environment Setup

Clone the repository and sync the virtual environment (including dev dependencies):
```bash
uv sync
```

---

## 📘 Usage

Both fetchers return a standardized `pandas.DataFrame` matching the schema defined in `src/config.py`.

### Fetching with `yfinance`

```python
from datetime import datetime, timedelta
from src.logger import setup_logging, get_logger
from src.data_fetchers import fetch_yfinance_ohlcv

setup_logging(default_level="INFO", console_output=True)
logger = get_logger(__name__)

start_date = datetime.now() - timedelta(days=15)
end_date = datetime.now()

try:
    df = fetch_yfinance_ohlcv(ticker="TCS", start_date=start_date, end_date=end_date)
    logger.info("Successfully fetched data!")
    print(df.head())
except Exception as e:
    logger.error(f"Failed to fetch data: {e}")
```

### Fetching from NSE directly with `jugaad-data`

```python
from datetime import date
from src.logger import setup_logging, get_logger
from src.data_fetchers import fetch_jugaad_ohlcv

setup_logging(default_level="INFO")
logger = get_logger(__name__)

try:
    df = fetch_jugaad_ohlcv(
        symbol="RELIANCE.NS",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 20),
    )
    logger.info("Successfully loaded data from NSE!")
    print(df.head())
except Exception as e:
    logger.error(f"NSE ingestion failed: {e}")
```

---

## 🛡️ Exception Hierarchy & Data Schema

Exceptions are defined centrally in `src/exceptions.py` and shared across all fetcher adapters.

### Standardized Schema

Every returned DataFrame has:
- **Index**: `Date` — a timezone-naive `DatetimeIndex`, sorted ascending.
- **Columns**: `["Open", "High", "Low", "Close", "Volume"]`

### Exception Reference

| Exception | Raised When |
| :--- | :--- |
| `DataFetchError` | Base exception; generic parser failures or schema issues. |
| `TickerNotFoundError` | Ticker is invalid, delisted, or has no history. |
| `ConnectionError` | Network is down, rate-limited, or API timed out. |

---

## 🧪 Testing & Quality

### Unit Tests (offline, mocked)

```bash
# Run full test suite with coverage
uv run pytest tests/ --cov=src -v
```

> No `PYTHONPATH=.` prefix needed — configured via `[tool.pytest.ini_options]` in `pyproject.toml`.

### Linting & Formatting

```bash
uv run ruff check src/ tests/ scripts/
uv run ruff format src/ tests/ scripts/
```

### Developer Scripts

```bash
# Demonstrate the custom logger output
uv run python scripts/demo_logger.py

# Live integration smoke-test (requires internet, hits real NSE/Yahoo APIs)
uv run python scripts/run_fetchers.py
```
