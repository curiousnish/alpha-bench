"""
Central exception hierarchy for the Alpha-Bench data fetching layer.

All public-facing exceptions are defined here so they can be imported
consistently across fetcher modules and by downstream consumers without
creating circular imports.
"""


class DataFetchError(Exception):
    """Base exception for all data fetching operations."""

    pass


class TickerNotFoundError(DataFetchError):
    """Raised when a requested ticker/symbol cannot be found, is invalid, or is delisted."""

    pass


class ConnectionError(DataFetchError):
    """Raised when a network or connectivity issue prevents data retrieval."""

    pass
