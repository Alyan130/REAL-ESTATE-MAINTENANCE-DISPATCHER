"""
app/core/logging.py

Logging configuration.

Deliberately plain: the format carries level, logger name, and message only.
Per docs/rules/security.md nothing here captures request bodies, headers, or
tokens — a log formatter is exactly the place where credentials leak by accident.
"""
from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    """Install the root handler. Safe to call more than once."""
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT, force=True)

    # SQLAlchemy echoes every statement at INFO, which buries application logs
    # and can surface parameter values.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
