"""Workflow logging.

Every debugging session logs its key events (diagnosis, patches, test runs,
retries, final status) to logs/coach.log and keeps a copy in memory so the UI
can show a timeline. Source code and API keys are never written to the log:
events record file names, counts, and short summaries only.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler

from coach import config

_LOGGER_NAME = "coach"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            config.LOG_DIR / "coach.log", maxBytes=1_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # A read-only filesystem should not stop the coach from working.
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


@dataclass
class Event:
    time: str
    level: str
    message: str


@dataclass
class SessionLog:
    """Logs events for one debugging session, tagged with its session id."""

    session_id: str
    events: list[Event] = field(default_factory=list)

    def _log(self, level: int, message: str) -> None:
        get_logger().log(level, "[%s] %s", self.session_id, message)
        self.events.append(
            Event(datetime.now().strftime("%H:%M:%S"), logging.getLevelName(level), message)
        )

    def info(self, message: str) -> None:
        self._log(logging.INFO, message)

    def warning(self, message: str) -> None:
        self._log(logging.WARNING, message)

    def error(self, message: str) -> None:
        self._log(logging.ERROR, message)
