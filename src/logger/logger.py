import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class ColouredFormatter(logging.Formatter):
    """
    A custom logging formatter that adds ANSI color escape codes to log messages
    based on their severity level. Designed for development and terminal readability.
    """
    # ANSI escape sequences for terminal styling
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Text colors
    GREY = "\033[90m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    
    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD + RED,
    }

    def __init__(self, fmt: str, datefmt: str | None = None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.fmt = fmt

    def format(self, record: logging.LogRecord) -> str:
        # Save original values to restore them later
        orig_levelname = record.levelname
        orig_name = record.name
        orig_asctime = getattr(record, 'asctime', None)
        
        # Color the level name and format it to be 8 characters wide (excluding ANSI codes)
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        
        # Color the logger name slightly dim/grey for an aesthetic clean look
        record.name = f"{self.GREY}{record.name}{self.RESET}"
        
        # Generate time string if not already present
        if not orig_asctime:
            record.asctime = self.formatTime(record, self.datefmt)
        
        # Color the timestamp in dim grey
        record.asctime = f"{self.GREY}{record.asctime}{self.RESET}"
        
        # Format the record using standard logging.Formatter
        formatted_message = super().format(record)
        
        # Restore original values to prevent side effects on other handlers
        record.levelname = orig_levelname
        record.name = orig_name
        if orig_asctime is None:
            delattr(record, 'asctime')
        else:
            record.asctime = orig_asctime
            
        return formatted_message


def setup_logging(
    default_level: int | str = "INFO",
    log_file: str | None = None,
    console_output: bool = True,
) -> None:
    """
    Sets up the root logger configuration for the entire project.
    
    Args:
        default_level: The logging level threshold (e.g., "INFO", "DEBUG", logging.INFO).
        log_file: Optional path to a file where logs should be written.
        console_output: Whether to output logs to the console.
    """
    # Convert string level to logging level integer if necessary
    if isinstance(default_level, str):
        default_level = getattr(logging, default_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)

    # Clear any existing handlers to avoid duplicate logging (e.g., in Jupyter or re-runs)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Shared configurations
    date_format = "%Y-%m-%d %H:%M:%S"
    # Format pattern includes timestamp, level, logger name, source code location, and message
    log_format = "%(asctime)s | %(levelname)s | %(name)s:%(filename)s:%(lineno)d - %(message)s"

    # 1. Console Handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(default_level)
        
        # Check if the console supports color (is a TTY)
        if sys.stdout.isatty():
            formatter = ColouredFormatter(fmt=log_format, datefmt=date_format)
        else:
            # Plain formatter without colors for standard files/pipes
            plain_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(filename)s:%(lineno)d - %(message)s"
            formatter = logging.Formatter(fmt=plain_format, datefmt=date_format)
            
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 2. File Handler
    if log_file:
        # Resolve absolute path
        log_file_abs = os.path.abspath(log_file)
        
        # Create parent directory if it doesn't exist
        log_dir = os.path.dirname(log_file_abs)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Use rotating file handler: max 5MB per file, keep 5 backups
        file_handler = RotatingFileHandler(
            log_file_abs,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(default_level)
        
        # File formatter (strictly plain, no escape characters)
        file_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(filename)s:%(lineno)d - %(message)s"
        file_formatter = logging.Formatter(fmt=file_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Utility helper to retrieve a named logger.
    
    Args:
        name: Name of the logger, typically standard `__name__`.
    """
    return logging.getLogger(name)
