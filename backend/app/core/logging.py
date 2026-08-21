import logging
from logging import Logger, StreamHandler
from typing import Literal

LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
LOG_FORMAT = "timestamp=%(asctime)s level=%(levelname)s module=%(name)s message=%(message)s"


def configure_logging(level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
    """Configure the root logger for the backend application.

    This creates a single centralized logging configuration with a uniform
    format that includes timestamps, log levels, and module origins.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    logging.captureWarnings(True)


def get_logger(name: str) -> Logger:
    """Return a configured logger for the requested module name."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        configure_logging()
    return logging.getLogger(name)
